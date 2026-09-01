use std::collections::BTreeMap;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

pub const MAX_PARTICIPANTS: usize = 4;
pub const DEFAULT_SESSION_TTL: Duration = Duration::from_secs(8 * 60 * 60);

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Participant {
    pub id: String,
    pub display_name: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EventKind {
    Joined,
    Reconnected,
    Left,
    Removed,
    CommandProposed,
    CommandApproved,
    CommandRejected,
    CommandStarted,
    CommandFinished,
    SessionExpired,
    Notice,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SessionEvent {
    pub sequence: u64,
    pub timestamp: u64,
    pub actor_id: String,
    pub kind: EventKind,
    pub command_id: Option<String>,
    pub message: String,
}

#[derive(Debug, PartialEq, Eq)]
pub enum SessionError {
    Full,
    DuplicateParticipant,
    NotParticipant,
    UnknownCommand,
    NotAuthorized,
    InvalidCommand,
    InvalidInvite,
    Expired,
    AlreadyRemoved,
}

#[derive(Clone, Debug)]
struct CommandRequest {
    proposer: String,
    command: String,
    approved_by: Vec<String>,
}

#[derive(Clone, Debug)]
struct ParticipantState {
    participant: Participant,
    invite_token: String,
    connected: bool,
    removed: bool,
}

pub struct CollaborationSession {
    participants: BTreeMap<String, ParticipantState>,
    commands: BTreeMap<String, CommandRequest>,
    events: Vec<SessionEvent>,
    next_sequence: u64,
    created_at: u64,
    expires_at: u64,
}

impl Default for CollaborationSession {
    fn default() -> Self {
        Self::new()
    }
}

impl CollaborationSession {
    pub fn new() -> Self {
        Self::with_ttl(DEFAULT_SESSION_TTL)
    }

    pub fn with_ttl(ttl: Duration) -> Self {
        let now = unix_now();
        Self {
            participants: BTreeMap::new(),
            commands: BTreeMap::new(),
            events: Vec::new(),
            next_sequence: 0,
            created_at: now,
            expires_at: now.saturating_add(ttl.as_secs()),
        }
    }

    pub fn created_at(&self) -> u64 {
        self.created_at
    }
    pub fn expires_at(&self) -> u64 {
        self.expires_at
    }
    pub fn is_expired_at(&self, now: u64) -> bool {
        now >= self.expires_at
    }
    pub fn events(&self) -> &[SessionEvent] {
        &self.events
    }
    pub fn participants(&self) -> impl Iterator<Item = &Participant> {
        self.participants
            .values()
            .filter(|s| !s.removed)
            .map(|s| &s.participant)
    }

    pub fn invite(&self, participant_id: &str) -> Result<String, SessionError> {
        let state = self
            .participants
            .get(participant_id)
            .ok_or(SessionError::NotParticipant)?;
        if state.removed {
            return Err(SessionError::AlreadyRemoved);
        }
        Ok(state.invite_token.clone())
    }

    pub fn join(
        &mut self,
        participant: Participant,
        invite_token: &str,
    ) -> Result<(), SessionError> {
        self.ensure_active()?;
        if participant.id.is_empty() || invite_token.is_empty() {
            return Err(SessionError::InvalidInvite);
        }
        if let Some(existing) = self.participants.get_mut(&participant.id) {
            if existing.removed {
                return Err(SessionError::AlreadyRemoved);
            }
            if existing.invite_token != invite_token {
                return Err(SessionError::InvalidInvite);
            }
            existing.connected = true;
            self.record(
                participant.id,
                EventKind::Reconnected,
                None,
                "participant reconnected".into(),
            );
            return Ok(());
        }
        if self.participants.len() >= MAX_PARTICIPANTS {
            return Err(SessionError::Full);
        }
        let id = participant.id.clone();
        self.participants.insert(
            id.clone(),
            ParticipantState {
                participant: participant.clone(),
                invite_token: invite_token.into(),
                connected: true,
                removed: false,
            },
        );
        self.record(
            id,
            EventKind::Joined,
            None,
            format!("{} joined the session", participant.display_name),
        );
        Ok(())
    }

    pub fn disconnect(&mut self, participant_id: &str) -> Result<(), SessionError> {
        let state = self
            .participants
            .get_mut(participant_id)
            .ok_or(SessionError::NotParticipant)?;
        if state.removed {
            return Err(SessionError::AlreadyRemoved);
        }
        state.connected = false;
        self.record(
            participant_id.into(),
            EventKind::Left,
            None,
            "participant disconnected; reconnect is allowed before expiry".into(),
        );
        Ok(())
    }

    pub fn remove(&mut self, actor_id: &str, participant_id: &str) -> Result<(), SessionError> {
        self.require_participant(actor_id)?;
        let state = self
            .participants
            .get_mut(participant_id)
            .ok_or(SessionError::NotParticipant)?;
        if state.removed {
            return Err(SessionError::AlreadyRemoved);
        }
        state.removed = true;
        state.connected = false;
        self.record(
            actor_id.into(),
            EventKind::Removed,
            None,
            format!("participant {participant_id} removed"),
        );
        Ok(())
    }

    pub fn expire_if_needed(&mut self, now: u64) -> bool {
        if !self.is_expired_at(now) {
            return false;
        }
        if !self
            .events
            .iter()
            .any(|e| e.kind == EventKind::SessionExpired)
        {
            self.record(
                "system".into(),
                EventKind::SessionExpired,
                None,
                "session expired; new commands and reconnects are blocked".into(),
            );
        }
        true
    }

    pub fn propose(
        &mut self,
        actor_id: &str,
        command_id: &str,
        command: &str,
    ) -> Result<(), SessionError> {
        self.require_participant(actor_id)?;
        if command_id.is_empty()
            || command.len() > 512
            || command.chars().any(|c| c == '\n' || c == '\r')
        {
            return Err(SessionError::InvalidCommand);
        }
        if self.commands.contains_key(command_id) {
            return Err(SessionError::InvalidCommand);
        }
        self.commands.insert(
            command_id.into(),
            CommandRequest {
                proposer: actor_id.into(),
                command: command.into(),
                approved_by: Vec::new(),
            },
        );
        self.record(
            actor_id.into(),
            EventKind::CommandProposed,
            Some(command_id.into()),
            format!("command proposed: {command}"),
        );
        Ok(())
    }

    pub fn approve(&mut self, actor_id: &str, command_id: &str) -> Result<(), SessionError> {
        self.require_participant(actor_id)?;
        let request = self
            .commands
            .get_mut(command_id)
            .ok_or(SessionError::UnknownCommand)?;
        if !request.approved_by.iter().any(|id| id == actor_id) {
            request.approved_by.push(actor_id.into());
        }
        self.record(
            actor_id.into(),
            EventKind::CommandApproved,
            Some(command_id.into()),
            "command approval recorded".into(),
        );
        Ok(())
    }

    pub fn start(&mut self, actor_id: &str, command_id: &str) -> Result<String, SessionError> {
        self.require_participant(actor_id)?;
        let request = self
            .commands
            .get(command_id)
            .ok_or(SessionError::UnknownCommand)?;
        if request.proposer != actor_id && !request.approved_by.iter().any(|id| id == actor_id) {
            return Err(SessionError::NotAuthorized);
        }
        let command = request.command.clone();
        self.record(
            actor_id.into(),
            EventKind::CommandStarted,
            Some(command_id.into()),
            format!("command started through policy adapter: {command}"),
        );
        Ok(command)
    }

    pub fn finish(
        &mut self,
        actor_id: &str,
        command_id: &str,
        result_summary: &str,
    ) -> Result<(), SessionError> {
        self.require_participant(actor_id)?;
        if !self.commands.contains_key(command_id) {
            return Err(SessionError::UnknownCommand);
        }
        self.record(
            actor_id.into(),
            EventKind::CommandFinished,
            Some(command_id.into()),
            result_summary.chars().take(512).collect(),
        );
        Ok(())
    }

    fn require_participant(&self, actor_id: &str) -> Result<(), SessionError> {
        if self.is_expired_at(unix_now()) {
            return Err(SessionError::Expired);
        }
        match self.participants.get(actor_id) {
            Some(state) if !state.removed && state.connected => Ok(()),
            _ => Err(SessionError::NotParticipant),
        }
    }
    fn ensure_active(&self) -> Result<(), SessionError> {
        if self.is_expired_at(unix_now()) {
            Err(SessionError::Expired)
        } else {
            Ok(())
        }
    }
    fn record(
        &mut self,
        actor_id: String,
        kind: EventKind,
        command_id: Option<String>,
        message: String,
    ) {
        self.events.push(SessionEvent {
            sequence: self.next_sequence,
            timestamp: unix_now(),
            actor_id,
            kind,
            command_id,
            message,
        });
        self.next_sequence += 1;
    }
}

fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn user(id: &str) -> Participant {
        Participant {
            id: id.into(),
            display_name: id.into(),
        }
    }
    #[test]
    fn session_caps_at_four_users() {
        let mut s = CollaborationSession::new();
        for id in ["a", "b", "c", "d"] {
            s.join(user(id), id).unwrap();
        }
        assert_eq!(s.join(user("e"), "e"), Err(SessionError::Full));
    }
    #[test]
    fn invite_reconnect_and_remove_are_visible() {
        let mut s = CollaborationSession::new();
        s.join(user("a"), "a-token").unwrap();
        let token = s.invite("a").unwrap();
        s.disconnect("a").unwrap();
        s.join(user("a"), &token).unwrap();
        s.remove("a", "a").unwrap();
        assert_eq!(s.events().len(), 4);
        assert_eq!(s.join(user("a"), &token), Err(SessionError::AlreadyRemoved));
    }
    #[test]
    fn every_command_stage_is_visible() {
        let mut s = CollaborationSession::new();
        s.join(user("a"), "a").unwrap();
        s.join(user("b"), "b").unwrap();
        s.propose("a", "cmd-1", "socket-audit 127.0.0.1").unwrap();
        s.approve("b", "cmd-1").unwrap();
        s.start("b", "cmd-1").unwrap();
        s.finish("b", "cmd-1", "completed locally").unwrap();
        assert_eq!(s.events().len(), 6);
    }
    #[test]
    fn expired_session_blocks_new_work() {
        let mut s = CollaborationSession::with_ttl(Duration::from_secs(0));
        assert!(s.expire_if_needed(s.expires_at()));
        assert_eq!(s.join(user("a"), "a"), Err(SessionError::Expired));
    }
}
