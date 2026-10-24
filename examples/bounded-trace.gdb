set pagination off
set confirm off
set print thread-events off
set logging file .agents/evidence/bounded-trace.log
set logging overwrite on
set logging enabled on

set $hits = 0
break REPLACE_WITH_FUNCTION_OR_ADDRESS
commands
  silent
  set $hits = $hits + 1
  printf "hit=%u pc=%p\n", $hits, $pc
  bt 6
  if $hits >= 20
    detach
    quit
  end
  continue
end

continue
