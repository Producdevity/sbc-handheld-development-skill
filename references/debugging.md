# Native debugging and reverse engineering

First identify the failure layer: launcher, loader/interpreter, dynamic linking, syscall/ABI, renderer, audio, input, networking, or closed game code. Use the least invasive tool that can distinguish the hypotheses.

## Baseline inspection

Keep exact evidence for the deployed file:

```sh
file app
readelf -h -l -d -s -V app
sha256sum app
```

Inspect the target's ELF interpreter and libraries. Host symbols, executable, sysroot, and deployed libraries must match the target build. A successful cross-build does not prove the target kernel or libc provides the required ABI.

## Remote GDB

Prefer the SSH stdio transport. `gdbserver` has no authentication, and its `HOST:PORT` host component is currently ignored. Values such as `localhost:2345` or `127.0.0.1:2345` can still listen on every interface.

Run the transport from host GDB so SSH supplies authentication and no TCP listener is created on the handheld:

```gdb
target remote | ssh -T device gdbserver stdio /path/to/app arg...
target remote | ssh -T device gdbserver --attach stdio PID
target extended-remote | ssh -T device gdbserver --multi stdio
```

Use `target remote` for a program started or attached by gdbserver. Use `target extended-remote` for multi mode. Keep the target-side process under the normal frontend when investigating frontend-dependent behavior; attaching may be safer than relaunching it outside that lifecycle.

If TCP is unavoidable, restrict it outside gdbserver with a firewall or isolated network, verify the actual listener with `ss` or an equivalent tool, and close it immediately after the bounded session. Do not infer the bind address from the `HOST:PORT` argument.

Store repeatable GDB command files under `.agents/debug/`, not in global `.gdbinit`. Copy [remote.gdb](../examples/remote.gdb) and replace its local executable and sysroot paths. A minimal command file is:

```gdb
set pagination off
set confirm off
set print thread-events off
set logging file .agents/evidence/gdb-session.log
set logging overwrite on
set logging enabled on
file build/debug/app
set sysroot .agents/sysroot
set solib-search-path .agents/sysroot/lib:.agents/sysroot/usr/lib
target remote | ssh -T device gdbserver stdio /path/to/app
info sharedlibrary
info threads
```

Run it with the matching cross-GDB:

```sh
gdb-multiarch -q -x .agents/debug/remote.gdb
```

## Missing target tools

Missing debugger and tracer packages are normal on appliance-style CFW images. Treat absence as a target capability, not as an automatic installation task.

1. Decide whether the requested evidence can be obtained from existing logs, `/proc`, core files, native GDB, or another already-installed tool.
2. If not, inspect the CFW's package model, repository configuration, free space, architecture, libc, kernel, and persistence rules.
3. Propose the minimal tool set and ask for permission before changing the device. Installing `gdbserver` alone is usually enough for remote debugging; target-side `gdb` is optional.
4. Do not include `perf` by default. Its userspace package and the target kernel must be compatible, and the kernel must expose the required events.
5. After installation, record package versions and test the tool against a harmless program before attaching it to the application. Confirm that no server, trace, temporary file, or changed frontend state remains.

On a read-only or image-managed CFW, do not force a package-manager installation. A compatible, provenance-checked transient binary may be copied to `/tmp` with permission, but that is a per-session diagnostic rather than a permanent dependency.

For a bounded breakpoint trace, start from [bounded-trace.gdb](../examples/bounded-trace.gdb). Its counter detaches after 20 hits; the host invocation still needs a wall-clock timeout in case the breakpoint is never reached.

A smaller inline form is:

```gdb
set $hits = 0
break function_name
commands
  silent
  set $hits = $hits + 1
  printf "hit=%u function=function_name\n", $hits
  if $hits >= 20
    detach
    quit
  end
  continue
end
continue
```

Avoid unbounded breakpoints in frame, audio, or packet hot paths. Use counters, conditions, sampling, or a one-shot disable command.

For PIE/shared-library addresses, obtain the live mappings and calculate the load bias. Do not reuse static virtual addresses from another build. Save module hashes with every address-based result.

## Crashes and hangs

- Capture the application log, exit status, kernel message window, and matching binaries first.
- For a crash, preserve a core only when storage and privacy permit; pair it with the exact executable and libraries.
- For a hang, collect thread backtraces before killing the process.
- Bound `strace` by syscall set, duration, and output size.
- Use `perf` only if the target kernel permits it and the experiment needs sampling.
- Do not disable ASLR, ptrace restrictions, watchdogs, or security settings globally for convenience.

## Ghidra, radare2/r2, Rizin, and binary inspection

Use project-local scripts under `.agents/tools/` for repeatable import labeling, xref collection, decompilation, or binary-format parsing. Record:

- input file hash and load base;
- architecture/mode and relocation assumptions;
- tool version and script arguments;
- addresses as module-relative offsets where possible;
- generated output under `.agents/evidence/`.

Ghidra post-scripts, `r2`/Rizin command files, raw Thumb scanners, and S3E/import-table parsers solve different problems. Do not merge them into a generic scanner or treat a string/constant match as behavioral proof. Correlate static findings with a bounded runtime trace when possible.

Keep proprietary binaries, extracted assets, decompiler databases, and unsanitized dumps out of the repository unless redistribution is explicitly allowed. Public documentation should record provenance and conclusions, not private artifacts.

## Primary references

- <https://sourceware.org/gdb/current/onlinedocs/gdb.html/Server.html>
- <https://sourceware.org/gdb/current/onlinedocs/gdb.html/Connecting.html>
- <https://docs.kernel.org/input/uinput.html>
