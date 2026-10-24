#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <math.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

#define ARRAY_SIZE(value) (sizeof(value) / sizeof((value)[0]))
#define COMMAND_LIMIT 256

enum device_kind {
  DEVICE_GAMEPAD,
  DEVICE_KEYBOARD,
  DEVICE_POINTER,
};

struct named_code {
  const char *name;
  uint16_t code;
};

struct axis {
  const char *name;
  uint16_t code;
  int32_t minimum;
  int32_t maximum;
  int32_t fuzz;
  int32_t flat;
};

struct gamepad_profile {
  const char *name;
  const char *device_name;
  struct input_id id;
  const struct named_code *buttons;
  size_t button_count;
  const struct axis *axes;
  size_t axis_count;
};

static const struct named_code generic_gamepad_buttons[] = {
    {"face.south", BTN_SOUTH},         {"face.east", BTN_EAST},
    {"face.west", BTN_WEST},           {"face.north", BTN_NORTH},
    {"shoulder.left", BTN_TL},         {"shoulder.right", BTN_TR},
    {"button.back", BTN_SELECT},       {"button.start", BTN_START},
    {"button.guide", BTN_MODE},        {"stick.left.press", BTN_THUMBL},
    {"stick.right.press", BTN_THUMBR},
};

static const struct axis generic_gamepad_axes[] = {
    {"stick.left.x", ABS_X, -32768, 32767, 0, 4096},
    {"stick.left.y", ABS_Y, -32768, 32767, 0, 4096},
    {"stick.right.x", ABS_RX, -32768, 32767, 0, 4096},
    {"stick.right.y", ABS_RY, -32768, 32767, 0, 4096},
    {"trigger.left", ABS_Z, 0, 255, 0, 0},
    {"trigger.right", ABS_RZ, 0, 255, 0, 0},
    {"dpad.x", ABS_HAT0X, -1, 1, 0, 0},
    {"dpad.y", ABS_HAT0Y, -1, 1, 0, 0},
};

static const struct named_code rk3326_go_super_buttons[] = {
    {"face.south", BTN_SOUTH},
    {"face.east", BTN_EAST},
    {"face.west", BTN_NORTH},
    {"face.north", BTN_WEST},
    {"shoulder.left", BTN_TL},
    {"shoulder.right", BTN_TR},
    {"trigger.left", BTN_TL2},
    {"trigger.right", BTN_TR2},
    {"dpad.up", BTN_DPAD_UP},
    {"dpad.down", BTN_DPAD_DOWN},
    {"dpad.left", BTN_DPAD_LEFT},
    {"dpad.right", BTN_DPAD_RIGHT},
    {"button.back", BTN_TRIGGER_HAPPY1},
    {"button.start", BTN_TRIGGER_HAPPY2},
    {"stick.left.press", BTN_TRIGGER_HAPPY3},
    {"stick.right.press", BTN_TRIGGER_HAPPY4},
    {"button.guide", BTN_TRIGGER_HAPPY5},
};

static const struct axis rk3326_go_super_axes[] = {
    {"stick.left.x", ABS_X, -1800, 1800, 32, 32},
    {"stick.left.y", ABS_Y, -1800, 1800, 32, 32},
    {"stick.right.x", ABS_RX, -1800, 1800, 32, 32},
    {"stick.right.y", ABS_RY, -1800, 1800, 32, 32},
};

static const struct gamepad_profile generic_gamepad_profile = {
    .name = "generic",
    .device_name = "Handheld Development Gamepad",
    .id = {.bustype = BUS_USB, .vendor = 0x1209, .product = 1, .version = 1},
    .buttons = generic_gamepad_buttons,
    .button_count = ARRAY_SIZE(generic_gamepad_buttons),
    .axes = generic_gamepad_axes,
    .axis_count = ARRAY_SIZE(generic_gamepad_axes),
};

static const struct gamepad_profile rk3326_go_super_profile = {
    .name = "rk3326-go-super",
    .device_name = "GO-Super Gamepad",
    .id = {.bustype = BUS_HOST,
           .vendor = 0x484b,
           .product = 0x1100,
           .version = 0x0100},
    .buttons = rk3326_go_super_buttons,
    .button_count = ARRAY_SIZE(rk3326_go_super_buttons),
    .axes = rk3326_go_super_axes,
    .axis_count = ARRAY_SIZE(rk3326_go_super_axes),
};

static const struct named_code xbox360_buttons[] = {
    {"face.south", BTN_A},            {"face.east", BTN_B},
    {"face.west", BTN_X},             {"face.north", BTN_Y},
    {"shoulder.left", BTN_TL},        {"shoulder.right", BTN_TR},
    {"button.back", BTN_SELECT},      {"button.start", BTN_START},
    {"button.guide", BTN_MODE},       {"stick.left.press", BTN_THUMBL},
    {"stick.right.press", BTN_THUMBR},
};

static const struct gamepad_profile xbox360_profile = {
    .name = "xbox360",
    .device_name = "Xbox 360 Controller",
    .id = {.bustype = BUS_USB,
           .vendor = 0x045e,
           .product = 0x028e,
           .version = 0x0114},
    .buttons = xbox360_buttons,
    .button_count = ARRAY_SIZE(xbox360_buttons),
    .axes = generic_gamepad_axes,
    .axis_count = ARRAY_SIZE(generic_gamepad_axes),
};

static const struct gamepad_profile *gamepad_profile =
    &generic_gamepad_profile;

static const struct named_code keyboard_keys[] = {
    {"key.a", KEY_A},
    {"key.b", KEY_B},
    {"key.c", KEY_C},
    {"key.d", KEY_D},
    {"key.e", KEY_E},
    {"key.f", KEY_F},
    {"key.g", KEY_G},
    {"key.h", KEY_H},
    {"key.i", KEY_I},
    {"key.j", KEY_J},
    {"key.k", KEY_K},
    {"key.l", KEY_L},
    {"key.m", KEY_M},
    {"key.n", KEY_N},
    {"key.o", KEY_O},
    {"key.p", KEY_P},
    {"key.q", KEY_Q},
    {"key.r", KEY_R},
    {"key.s", KEY_S},
    {"key.t", KEY_T},
    {"key.u", KEY_U},
    {"key.v", KEY_V},
    {"key.w", KEY_W},
    {"key.x", KEY_X},
    {"key.y", KEY_Y},
    {"key.z", KEY_Z},
    {"key.0", KEY_0},
    {"key.1", KEY_1},
    {"key.2", KEY_2},
    {"key.3", KEY_3},
    {"key.4", KEY_4},
    {"key.5", KEY_5},
    {"key.6", KEY_6},
    {"key.7", KEY_7},
    {"key.8", KEY_8},
    {"key.9", KEY_9},
    {"key.escape", KEY_ESC},
    {"key.enter", KEY_ENTER},
    {"key.space", KEY_SPACE},
    {"key.tab", KEY_TAB},
    {"key.backspace", KEY_BACKSPACE},
    {"key.up", KEY_UP},
    {"key.down", KEY_DOWN},
    {"key.left", KEY_LEFT},
    {"key.right", KEY_RIGHT},
    {"key.home", KEY_HOME},
    {"key.end", KEY_END},
    {"key.page-up", KEY_PAGEUP},
    {"key.page-down", KEY_PAGEDOWN},
    {"key.left-ctrl", KEY_LEFTCTRL},
    {"key.left-alt", KEY_LEFTALT},
    {"key.left-shift", KEY_LEFTSHIFT},
};

static const struct named_code pointer_buttons[] = {
    {"pointer.primary", BTN_LEFT},
    {"pointer.secondary", BTN_RIGHT},
    {"pointer.middle", BTN_MIDDLE},
};

static const struct named_code pointer_axes[] = {
    {"pointer.x", REL_X},
    {"pointer.y", REL_Y},
    {"pointer.wheel", REL_WHEEL},
    {"pointer.hwheel", REL_HWHEEL},
};

static bool dpad_up;
static bool dpad_down;
static bool dpad_left;
static bool dpad_right;
static volatile sig_atomic_t stop_requested;
static bool release_on_exit = true;

static void request_stop(int signal_number) {
  (void)signal_number;
  stop_requested = 1;
}

static int sleep_ms(long milliseconds) {
  struct timespec duration = {
      .tv_sec = milliseconds / 1000,
      .tv_nsec = milliseconds % 1000 * 1000000,
  };
  while (nanosleep(&duration, &duration) < 0) {
    if (errno != EINTR) {
      return -1;
    }
    if (stop_requested) {
      return 0;
    }
  }
  return 0;
}

static int write_all(int fd, const void *data, size_t size) {
  const unsigned char *cursor = data;
  while (size > 0) {
    ssize_t written = write(fd, cursor, size);
    if (written < 0 && errno == EINTR) {
      continue;
    }
    if (written <= 0) {
      return -1;
    }
    cursor += written;
    size -= (size_t)written;
  }
  return 0;
}

static int write_event(int fd, uint16_t type, uint16_t code, int32_t value) {
  struct input_event event = {0};
  event.type = type;
  event.code = code;
  event.value = value;
  return write_all(fd, &event, sizeof(event));
}

static int synchronize(int fd) {
  return write_event(fd, EV_SYN, SYN_REPORT, 0);
}

static const struct named_code *find_code(const struct named_code *codes,
                                          size_t count, const char *name) {
  for (size_t index = 0; index < count; ++index) {
    if (strcmp(name, codes[index].name) == 0) {
      return &codes[index];
    }
  }
  return NULL;
}

static const struct axis *find_axis(const char *name) {
  for (size_t index = 0; index < gamepad_profile->axis_count; ++index) {
    if (strcmp(name, gamepad_profile->axes[index].name) == 0) {
      return &gamepad_profile->axes[index];
    }
  }
  return NULL;
}

static int set_axis(int fd, const struct axis *axis, int32_t value) {
  if (value < axis->minimum) {
    value = axis->minimum;
  } else if (value > axis->maximum) {
    value = axis->maximum;
  }
  return write_event(fd, EV_ABS, axis->code, value);
}

static int set_dpad(int fd, const char *name, bool pressed) {
  if (strcmp(name, "dpad.up") == 0) {
    dpad_up = pressed;
  } else if (strcmp(name, "dpad.down") == 0) {
    dpad_down = pressed;
  } else if (strcmp(name, "dpad.left") == 0) {
    dpad_left = pressed;
  } else if (strcmp(name, "dpad.right") == 0) {
    dpad_right = pressed;
  } else {
    return 1;
  }
  const struct axis *horizontal = find_axis("dpad.x");
  const struct axis *vertical = find_axis("dpad.y");
  if (set_axis(fd, horizontal, (int32_t)dpad_right - (int32_t)dpad_left) < 0 ||
      set_axis(fd, vertical, (int32_t)dpad_down - (int32_t)dpad_up) < 0) {
    return -1;
  }
  return 0;
}

static int set_gamepad_control(int fd, const char *name, bool pressed) {
  const struct named_code *button =
      find_code(gamepad_profile->buttons, gamepad_profile->button_count, name);
  if (button != NULL) {
    return write_event(fd, EV_KEY, button->code, pressed ? 1 : 0);
  }
  int dpad_result = set_dpad(fd, name, pressed);
  if (dpad_result <= 0) {
    return dpad_result;
  }
  const struct axis *axis = find_axis(name);
  if (axis != NULL && (axis->code == ABS_Z || axis->code == ABS_RZ)) {
    return set_axis(fd, axis, pressed ? axis->maximum : axis->minimum);
  }
  errno = EINVAL;
  return -1;
}

static int set_control(int fd, enum device_kind kind, const char *name,
                       bool pressed) {
  if (kind == DEVICE_GAMEPAD) {
    return set_gamepad_control(fd, name, pressed);
  }
  const struct named_code *codes =
      kind == DEVICE_KEYBOARD ? keyboard_keys : pointer_buttons;
  size_t count = kind == DEVICE_KEYBOARD ? ARRAY_SIZE(keyboard_keys)
                                         : ARRAY_SIZE(pointer_buttons);
  const struct named_code *control = find_code(codes, count, name);
  if (control == NULL) {
    errno = EINVAL;
    return -1;
  }
  return write_event(fd, EV_KEY, control->code, pressed ? 1 : 0);
}

static int set_normalized_axis(int fd, const char *name,
                               const char *raw_value) {
  const struct axis *axis = find_axis(name);
  if (axis == NULL || axis->code == ABS_HAT0X || axis->code == ABS_HAT0Y) {
    errno = EINVAL;
    return -1;
  }
  char *end = NULL;
  errno = 0;
  double value = strtod(raw_value, &end);
  if (errno != 0 || end == raw_value || *end != '\0' || !isfinite(value) ||
      value < -1.0 || value > 1.0 ||
      ((axis->code == ABS_Z || axis->code == ABS_RZ) && value < 0.0)) {
    errno = EINVAL;
    return -1;
  }
  double scaled = axis->minimum == 0
                      ? value * axis->maximum
                      : axis->minimum + (value + 1.0) *
                                            (axis->maximum - axis->minimum) /
                                            2.0;
  if (axis->minimum != 0 && value == 0.0) {
    scaled = 0.0;
  }
  return set_axis(fd, axis, (int32_t)lround(scaled));
}

static int move_pointer(int fd, const char *name, const char *raw_value) {
  const struct named_code *axis =
      find_code(pointer_axes, ARRAY_SIZE(pointer_axes), name);
  if (axis == NULL) {
    errno = EINVAL;
    return -1;
  }
  char *end = NULL;
  errno = 0;
  long value = strtol(raw_value, &end, 10);
  if (errno != 0 || end == raw_value || *end != '\0' || value < -32768 ||
      value > 32767) {
    errno = EINVAL;
    return -1;
  }
  return write_event(fd, EV_REL, axis->code, (int32_t)value);
}

static int release_all(int fd, enum device_kind kind) {
  int result = 0;
  const struct named_code *codes = NULL;
  size_t count = 0;
  if (kind == DEVICE_GAMEPAD) {
    codes = gamepad_profile->buttons;
    count = gamepad_profile->button_count;
  } else if (kind == DEVICE_KEYBOARD) {
    codes = keyboard_keys;
    count = ARRAY_SIZE(keyboard_keys);
  } else {
    codes = pointer_buttons;
    count = ARRAY_SIZE(pointer_buttons);
  }
  for (size_t index = 0; index < count; ++index) {
    if (write_event(fd, EV_KEY, codes[index].code, 0) < 0) {
      result = -1;
    }
  }
  if (kind == DEVICE_GAMEPAD) {
    dpad_up = dpad_down = dpad_left = dpad_right = false;
    for (size_t index = 0; index < gamepad_profile->axis_count; ++index) {
      const struct axis *axis = &gamepad_profile->axes[index];
      int32_t neutral = axis->minimum == 0 ? axis->minimum : 0;
      if (set_axis(fd, axis, neutral) < 0) {
        result = -1;
      }
    }
  }
  if (synchronize(fd) < 0) {
    result = -1;
  }
  return result;
}

static int execute_command(int fd, enum device_kind kind, char *line,
                           char *error, size_t error_size) {
  char *save = NULL;
  char *operation = strtok_r(line, " \t\r\n", &save);
  char *control = strtok_r(NULL, " \t\r\n", &save);
  char *value = strtok_r(NULL, " \t\r\n", &save);
  char *extra = strtok_r(NULL, " \t\r\n", &save);

  if (operation == NULL || extra != NULL) {
    snprintf(error, error_size, "invalid command");
    return -1;
  }
  if (strcmp(operation, "release-all") == 0 && control == NULL) {
    return release_all(fd, kind);
  }
  if (strcmp(operation, "quit") == 0 && control == NULL) {
    stop_requested = 1;
    return release_all(fd, kind);
  }
  if (strcmp(operation, "destroy") == 0 && control == NULL) {
    release_on_exit = false;
    stop_requested = 1;
    return 0;
  }
  if ((strcmp(operation, "down") == 0 || strcmp(operation, "up") == 0) &&
      control != NULL && value == NULL) {
    if (set_control(fd, kind, control, strcmp(operation, "down") == 0) == 0 &&
        synchronize(fd) == 0) {
      return 0;
    }
    snprintf(error, error_size, "unsupported control: %s", control);
    return -1;
  }
  if (strcmp(operation, "axis") == 0 && kind == DEVICE_GAMEPAD &&
      control != NULL && value != NULL) {
    if (set_normalized_axis(fd, control, value) == 0 && synchronize(fd) == 0) {
      return 0;
    }
    snprintf(error, error_size, "invalid axis or value: %s %s", control, value);
    return -1;
  }
  if (strcmp(operation, "move") == 0 && kind == DEVICE_POINTER &&
      control != NULL && value != NULL) {
    if (move_pointer(fd, control, value) == 0 && synchronize(fd) == 0) {
      return 0;
    }
    snprintf(error, error_size, "invalid pointer move: %s %s", control, value);
    return -1;
  }
  snprintf(error, error_size, "operation is not supported by this device");
  return -1;
}

static int configure_event_type(int fd, unsigned long request, int code,
                                const char *description) {
  if (ioctl(fd, request, code) < 0) {
    perror(description);
    return -1;
  }
  return 0;
}

static int create_device(enum device_kind kind) {
  int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0) {
    perror("open /dev/uinput");
    return -1;
  }
  if (configure_event_type(fd, UI_SET_EVBIT, EV_SYN,
                           "configure synchronization") < 0 ||
      configure_event_type(fd, UI_SET_EVBIT, EV_KEY, "configure keys") < 0) {
    close(fd);
    return -1;
  }

  const struct named_code *keys = NULL;
  size_t key_count = 0;
  if (kind == DEVICE_GAMEPAD) {
    keys = gamepad_profile->buttons;
    key_count = gamepad_profile->button_count;
  } else if (kind == DEVICE_KEYBOARD) {
    keys = keyboard_keys;
    key_count = ARRAY_SIZE(keyboard_keys);
  } else {
    keys = pointer_buttons;
    key_count = ARRAY_SIZE(pointer_buttons);
  }
  for (size_t index = 0; index < key_count; ++index) {
    if (configure_event_type(fd, UI_SET_KEYBIT, keys[index].code,
                             "configure key") < 0) {
      close(fd);
      return -1;
    }
  }

  struct uinput_user_dev setup = {0};
  if (kind == DEVICE_GAMEPAD) {
    setup.id = gamepad_profile->id;
    snprintf(setup.name, sizeof(setup.name), "%s",
             gamepad_profile->device_name);
    if (configure_event_type(fd, UI_SET_EVBIT, EV_ABS, "configure axes") < 0) {
      close(fd);
      return -1;
    }
    for (size_t index = 0; index < gamepad_profile->axis_count; ++index) {
      const struct axis *axis = &gamepad_profile->axes[index];
      if (configure_event_type(fd, UI_SET_ABSBIT, axis->code,
                               "configure axis") < 0) {
        close(fd);
        return -1;
      }
      setup.absmin[axis->code] = axis->minimum;
      setup.absmax[axis->code] = axis->maximum;
      setup.absfuzz[axis->code] = axis->fuzz;
      setup.absflat[axis->code] = axis->flat;
    }
  } else if (kind == DEVICE_KEYBOARD) {
    setup.id.bustype = BUS_USB;
    setup.id.vendor = 0x1209;
    setup.id.product = (uint16_t)kind + 1;
    setup.id.version = 1;
    snprintf(setup.name, sizeof(setup.name), "Handheld Development Keyboard");
  } else {
    setup.id.bustype = BUS_USB;
    setup.id.vendor = 0x1209;
    setup.id.product = (uint16_t)kind + 1;
    setup.id.version = 1;
    snprintf(setup.name, sizeof(setup.name), "Handheld Development Pointer");
    if (configure_event_type(fd, UI_SET_EVBIT, EV_REL,
                             "configure relative axes") < 0) {
      close(fd);
      return -1;
    }
    for (size_t index = 0; index < ARRAY_SIZE(pointer_axes); ++index) {
      if (configure_event_type(fd, UI_SET_RELBIT, pointer_axes[index].code,
                               "configure relative axis") < 0) {
        close(fd);
        return -1;
      }
    }
  }

  if (write_all(fd, &setup, sizeof(setup)) < 0 ||
      ioctl(fd, UI_DEV_CREATE) < 0) {
    perror("create uinput device");
    close(fd);
    return -1;
  }
  return fd;
}

static int open_listener(const char *socket_path) {
  if (strlen(socket_path) >= sizeof(((struct sockaddr_un *)0)->sun_path)) {
    fprintf(stderr, "socket path is too long\n");
    return -1;
  }
  struct stat status;
  if (lstat(socket_path, &status) == 0) {
    if (!S_ISSOCK(status.st_mode)) {
      fprintf(stderr, "refusing to replace non-socket path: %s\n", socket_path);
      return -1;
    }
    if (unlink(socket_path) < 0) {
      perror("remove stale socket");
      return -1;
    }
  } else if (errno != ENOENT) {
    perror("inspect socket path");
    return -1;
  }

  int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
  if (fd < 0) {
    perror("create control socket");
    return -1;
  }
  struct sockaddr_un address = {.sun_family = AF_UNIX};
  snprintf(address.sun_path, sizeof(address.sun_path), "%s", socket_path);
  if (bind(fd, (struct sockaddr *)&address, sizeof(address)) < 0 ||
      chmod(socket_path, 0600) < 0 || listen(fd, 8) < 0) {
    perror("prepare control socket");
    close(fd);
    unlink(socket_path);
    return -1;
  }
  return fd;
}

static ssize_t read_command(int client, char *command, size_t capacity) {
  size_t used = 0;
  while (used + 1 < capacity) {
    ssize_t length = read(client, command + used, capacity - used - 1);
    if (length < 0 && errno == EINTR) {
      continue;
    }
    if (length <= 0) {
      break;
    }
    used += (size_t)length;
    if (memchr(command, '\n', used) != NULL) {
      break;
    }
  }
  command[used] = '\0';
  return (ssize_t)used;
}

static int serve_client(int client, int device, enum device_kind kind) {
  struct timeval timeout = {.tv_sec = 3, .tv_usec = 0};
  setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
  setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
  char command[COMMAND_LIMIT];
  ssize_t length = read_command(client, command, sizeof(command));
  if (length <= 0) {
    return -1;
  }
  if (memchr(command, '\n', (size_t)length) == NULL) {
    write(client, "error: command too long\n", 24);
    return -1;
  }
  char error[160] = {0};
  if (execute_command(device, kind, command, error, sizeof(error)) == 0) {
    return write(client, "ok\n", 3) == 3 ? 0 : -1;
  }
  dprintf(client, "error: %s\n", error[0] ? error : strerror(errno));
  return -1;
}

static int serve(enum device_kind kind, const char *socket_path, long settle_ms,
                 const struct gamepad_profile *profile) {
  gamepad_profile = profile;
  int device = create_device(kind);
  if (device < 0) {
    return 1;
  }
  int listener = open_listener(socket_path);
  if (listener < 0) {
    ioctl(device, UI_DEV_DESTROY);
    close(device);
    return 1;
  }

  struct sigaction action = {0};
  action.sa_handler = request_stop;
  sigemptyset(&action.sa_mask);
  sigaction(SIGINT, &action, NULL);
  sigaction(SIGTERM, &action, NULL);
  signal(SIGPIPE, SIG_IGN);
  if (sleep_ms(settle_ms) < 0) {
    perror("wait for input registration");
    release_all(device, kind);
    ioctl(device, UI_DEV_DESTROY);
    close(device);
    close(listener);
    unlink(socket_path);
    return 1;
  }
  if (stop_requested) {
    release_all(device, kind);
    ioctl(device, UI_DEV_DESTROY);
    close(device);
    close(listener);
    unlink(socket_path);
    return 0;
  }
  printf("ready %s\n", socket_path);
  fflush(stdout);

  int result = 0;
  while (!stop_requested) {
    struct pollfd poll_fd = {.fd = listener, .events = POLLIN};
    int ready = poll(&poll_fd, 1, 250);
    if (ready < 0 && errno == EINTR) {
      continue;
    }
    if (ready < 0) {
      perror("poll control socket");
      result = 1;
      break;
    }
    if (ready == 0) {
      continue;
    }
    int client = accept(listener, NULL, NULL);
    if (client < 0) {
      if (errno != EINTR) {
        perror("accept control command");
        result = 1;
      }
      continue;
    }
    fcntl(client, F_SETFD, FD_CLOEXEC);
    serve_client(client, device, kind);
    close(client);
  }

  if (release_on_exit) {
    release_all(device, kind);
  }
  ioctl(device, UI_DEV_DESTROY);
  close(device);
  close(listener);
  unlink(socket_path);
  return result;
}

static int send_command(int argc, char **argv) {
  const char *socket_path = argv[2];
  int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
  if (fd < 0) {
    perror("create control connection");
    return 1;
  }
  struct sockaddr_un address = {.sun_family = AF_UNIX};
  if (strlen(socket_path) >= sizeof(address.sun_path)) {
    fprintf(stderr, "socket path is too long\n");
    close(fd);
    return 2;
  }
  snprintf(address.sun_path, sizeof(address.sun_path), "%s", socket_path);
  if (connect(fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
    perror("connect control socket");
    close(fd);
    return 1;
  }
  for (int index = 3; index < argc; ++index) {
    if (strpbrk(argv[index], " \t\r\n") != NULL ||
        dprintf(fd, "%s%s", index == 3 ? "" : " ", argv[index]) < 0) {
      fprintf(stderr, "invalid command argument\n");
      close(fd);
      return 2;
    }
  }
  if (write(fd, "\n", 1) != 1 || shutdown(fd, SHUT_WR) < 0) {
    perror("send control command");
    close(fd);
    return 1;
  }

  char response[192];
  ssize_t length = read(fd, response, sizeof(response) - 1);
  close(fd);
  if (length <= 0) {
    fprintf(stderr, "input service returned no response\n");
    return 1;
  }
  response[length] = '\0';
  if (strcmp(response, "ok\n") == 0) {
    return 0;
  }
  fputs(response, stderr);
  return 1;
}

static int parse_kind(const char *name, enum device_kind *kind) {
  if (strcmp(name, "gamepad") == 0) {
    *kind = DEVICE_GAMEPAD;
  } else if (strcmp(name, "keyboard") == 0) {
    *kind = DEVICE_KEYBOARD;
  } else if (strcmp(name, "pointer") == 0) {
    *kind = DEVICE_POINTER;
  } else {
    return -1;
  }
  return 0;
}

static const struct gamepad_profile *find_gamepad_profile(const char *name) {
  const struct gamepad_profile *profiles[] = {
      &generic_gamepad_profile,
      &rk3326_go_super_profile,
      &xbox360_profile,
  };
  for (size_t index = 0; index < ARRAY_SIZE(profiles); ++index) {
    if (strcmp(name, profiles[index]->name) == 0) {
      return profiles[index];
    }
  }
  return NULL;
}

static void usage(const char *program) {
  fprintf(stderr,
          "usage:\n  %s serve DEVICE SOCKET [SETTLE_MS [PROFILE]]\n"
          "  %s send SOCKET OPERATION [ARGUMENT ...]\n"
          "DEVICE is gamepad, keyboard, or pointer\n"
          "gamepad PROFILE is generic, rk3326-go-super, or xbox360\n",
          program, program);
}

int main(int argc, char **argv) {
  if (argc == 2 && strcmp(argv[1], "--help") == 0) {
    usage(argv[0]);
    return 0;
  }
  if (argc >= 4 && argc <= 6 && strcmp(argv[1], "serve") == 0) {
    enum device_kind kind;
    if (parse_kind(argv[2], &kind) < 0) {
      fprintf(stderr, "DEVICE must be gamepad, keyboard, or pointer\n");
      return 2;
    }
    long settle_ms = 750;
    if (argc >= 5) {
      char *end = NULL;
      errno = 0;
      settle_ms = strtol(argv[4], &end, 10);
      if (errno != 0 || end == argv[4] || *end != '\0' || settle_ms < 0 ||
          settle_ms > 10000) {
        fprintf(stderr, "SETTLE_MS must be between 0 and 10000\n");
        return 2;
      }
    }
    const struct gamepad_profile *profile = &generic_gamepad_profile;
    if (argc == 6) {
      if (kind != DEVICE_GAMEPAD ||
          (profile = find_gamepad_profile(argv[5])) == NULL) {
        fprintf(stderr,
                "PROFILE is supported only for gamepad and must be generic, "
                "rk3326-go-super, or xbox360\n");
        return 2;
      }
    }
    return serve(kind, argv[3], settle_ms, profile);
  }
  if (argc >= 4 && strcmp(argv[1], "send") == 0) {
    return send_command(argc, argv);
  }
  usage(argv[0]);
  return 2;
}
