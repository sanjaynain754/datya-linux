// SPDX-License-Identifier: GPL-2.0
/*
 * Datya Guardian: experimental, read-only kernel evidence sensor.
 *
 * This module does not block traffic, hide activity, bypass controls, or send
 * data off-host. It emits rate-limited metadata to the kernel audit stream so
 * a local userspace collector can correlate events. It is not an IDS and must
 * not be treated as one. Build against the exact target kernel headers.
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/ratelimit.h>
#include <linux/sched.h>
#include <linux/tracepoint.h>
#include <linux/net.h>
#include <net/sock.h>

#include <trace/events/sched.h>
#include <trace/events/sock.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Datya Linux contributors");
MODULE_DESCRIPTION("Read-only, rate-limited kernel evidence sensor for Datya Linux");
MODULE_VERSION("0.1.0");

static bool enabled = true;
module_param(enabled, bool, 0600);
MODULE_PARM_DESC(enabled, "Enable Datya Guardian event collection (default: true)");

static void datya_exec(void *ignore, struct task_struct *task, pid_t old_pid,
                       struct linux_binprm *bprm)
{
    if (!enabled || !bprm || !bprm->filename)
        return;

    pr_info_ratelimited("datya_guardian event=exec pid=%d uid=%u path=%s\n",
                        task_pid_nr(task), __kuid_val(current_uid()),
                        bprm->filename);
}

static void datya_socket_state(void *ignore, struct sock *sk,
                               int oldstate, int newstate)
{
    /* Only state transitions are recorded; payloads and packet contents are
     * never inspected. Userspace can apply policy and resolve addresses. */
    if (!enabled || !sk || sk->sk_family != AF_INET)
        return;

    pr_info_ratelimited("datya_guardian event=socket pid=%d proto=%u old=%d new=%d\n",
                        task_pid_nr(current), sk->sk_protocol,
                        oldstate, newstate);
}

static int __init datya_guardian_init(void)
{
    int ret;

    ret = register_trace_sched_process_exec(datya_exec, NULL);
    if (ret)
        return ret;

    ret = register_trace_inet_sock_set_state(datya_socket_state, NULL);
    if (ret) {
        unregister_trace_sched_process_exec(datya_exec, NULL);
        return ret;
    }

    pr_info("datya_guardian loaded: read-only local evidence enabled\n");
    return 0;
}

static void __exit datya_guardian_exit(void)
{
    unregister_trace_inet_sock_set_state(datya_socket_state, NULL);
    unregister_trace_sched_process_exec(datya_exec, NULL);
    tracepoint_synchronize_unregister();
    pr_info("datya_guardian unloaded\n");
}

module_init(datya_guardian_init);
module_exit(datya_guardian_exit);
