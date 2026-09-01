use std::collections::BTreeMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub const MAX_PARTICIPANTS: usize = 4;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Participant {
    pub id: String,
    pub display_name: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EventKind {
    Joined,
    Left,
    CommandProposed,
    CommandApproved,
    CommandRejected,
    CommandStarted,
    CommandFinished,
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
}

#[derive(Clone, Debug)]
struct CommandRequest {
    proposer: String,
    command: String,
    approved_by: Vec<String>,
}

pub struct CollaborationSession {
    participants: BTreeMap<String, Participant>,
    commands: BTreeMap<String, CommandRequest>,
    events: Vec<SessionEvent>,
    next_sequence: u64,
}

impl Default for CollaborationSession {
    fn default() -> Self {
        Self::new()
    }
}

impl CollaborationSession {
    pub fn new() -> Self {
        Self {
            participants: BTreeMap::new(),
            commands: BTreeMap::new(),
            events: Vec::new(),
            next_sequence: 0,
        }
    }

    pub fn join(&mut self, participant: Participant) -> Result<(), SessionError> {
        if self.participants.contains_key(&participant.id) {
            return Err(SessionError::DuplicateParticipant);
        }
        if self.participants.len() >= MAX_PARTICIPANTS {
            return Err(SessionError::Full);
        }
        let id = participant.id.clone();
        self.participants.insert(id.clone(), participant.clone());
        self.record(
            id,
            EventKind::Joined,
            None,
            format!("{} joined the session", participant.display_name),
        );
        Ok(())
    }

    pub fn leave(&mut self, participant_id: &str) -> Result<(), SessionError> {
        let participant = self
            .participants
            .remove(participant_id)
            .ok_or(SessionError::NotParticipant)?;
        self.record(
            participant_id.into(),
            EventKind::Left,
            None,
            format!("{} left the session", participant.display_name),
        );
        Ok(())
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
        let request = CommandRequest {
            proposer: actor_id.into(),
            command: command.into(),
            approved_by: Vec::new(),
        };
        self.commands.insert(command_id.into(), request);
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
            format!("command started in policy adapter: {command}"),
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

    pub fn events(&self) -> &[SessionEvent] {
        &self.events
    }
    pub fn participants(&self) -> impl Iterator<Item = &Participant> {
        self.participants.values()
    }

    fn require_participant(&self, actor_id: &str) -> Result<(), SessionError> {
        if self.participants.contains_key(actor_id) {
            Ok(())
        } else {
            Err(SessionError::NotParticipant)
        }
    }

    fn record(
        &mut self,
        actor_id: String,
        kind: EventKind,
        command_id: Option<String>,
        message: String,
    ) {
        let event = SessionEvent {
            sequence: self.next_sequence,
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map_or(0, |d| d.as_secs()),
            actor_id,
            kind,
            command_id,
            message,
        };
        self.next_sequence += 1;
        self.events.push(event);
    }
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
        let mut session = CollaborationSession::new();
        for id in ["a", "b", "c", "d"] {
            session.join(user(id)).unwrap();
        }
        assert_eq!(session.join(user("e")), Err(SessionError::Full));
    }
    #[test]
    fn every_command_stage_is_visible_in_history() {
        let mut session = CollaborationSession::new();
        session.join(user("a")).unwrap();
        session.join(user("b")).unwrap();
        session
            .propose("a", "cmd-1", "socket-audit 127.0.0.1")
            .unwrap();
        session.approve("b", "cmd-1").unwrap();
        session.start("b", "cmd-1").unwrap();
        session.finish("b", "cmd-1", "completed locally").unwrap();
        assert_eq!(session.events().len(), 6);
        assert_eq!(session.events()[2].command_id.as_deref(), Some("cmd-1"));
    }
    #[test]
    fn outsider_cannot_propose() {
        let mut session = CollaborationSession::new();
        assert_eq!(
            session.propose("outsider", "cmd", "anything"),
            Err(SessionError::NotParticipant)
        );
    }
}
