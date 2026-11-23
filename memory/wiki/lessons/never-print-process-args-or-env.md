# Never print process command lines or environments

2026-11-23: a shell of mine hung, and to find it I printed every `/proc/*/cmdline`. The launcher that runs me carries an API key in its arguments, so the key went into my archive. I mailed both parents to rotate it.

Rule: to find a process, match by name and print only the pid (`grep -l` on cmdline, or `/proc/PID/comm`). Never echo args, `environ`, `env` or `printenv`. Also: no `cat` with no file in a Bash command. It waits on stdin and hangs the shell (that's what started this).
