set pagination off
set confirm off
set print thread-events off

# Replace these paths with the exact local executable and captured target sysroot.
file /absolute/path/to/app
set sysroot /absolute/path/to/sysroot
set solib-search-path /absolute/path/to/sysroot/lib:/absolute/path/to/sysroot/usr/lib

# Replace the SSH host and target path. The stdio transport avoids an unauthenticated TCP listener.
target remote | ssh -T device gdbserver stdio /absolute/path/to/app
info sharedlibrary
info threads
