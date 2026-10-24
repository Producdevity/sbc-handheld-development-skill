#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/joystick.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static const char *axis_name(unsigned int code) {
  switch (code) {
  case ABS_X:
    return "ABS_X";
  case ABS_Y:
    return "ABS_Y";
  case ABS_Z:
    return "ABS_Z";
  case ABS_RX:
    return "ABS_RX";
  case ABS_RY:
    return "ABS_RY";
  case ABS_RZ:
    return "ABS_RZ";
  case ABS_HAT0X:
    return "ABS_HAT0X";
  case ABS_HAT0Y:
    return "ABS_HAT0Y";
  case ABS_BRAKE:
    return "ABS_BRAKE";
  case ABS_GAS:
    return "ABS_GAS";
  default:
    return NULL;
  }
}

static const char *button_name(unsigned int code) {
  switch (code) {
  case BTN_SOUTH:
    return "BTN_SOUTH";
  case BTN_EAST:
    return "BTN_EAST";
  case BTN_NORTH:
    return "BTN_NORTH";
  case BTN_WEST:
    return "BTN_WEST";
  case BTN_TL:
    return "BTN_TL";
  case BTN_TR:
    return "BTN_TR";
  case BTN_TL2:
    return "BTN_TL2";
  case BTN_TR2:
    return "BTN_TR2";
  case BTN_SELECT:
    return "BTN_SELECT";
  case BTN_START:
    return "BTN_START";
  case BTN_MODE:
    return "BTN_MODE";
  case BTN_THUMBL:
    return "BTN_THUMBL";
  case BTN_THUMBR:
    return "BTN_THUMBR";
  default:
    return NULL;
  }
}

int main(int argc, char **argv) {
  if (argc > 2 || (argc == 2 && strcmp(argv[1], "--help") == 0)) {
    fprintf(argc > 2 ? stderr : stdout, "usage: %s [/dev/input/jsN]\n",
            argv[0]);
    return argc > 2 ? 2 : 0;
  }
  const char *path = argc == 2 ? argv[1] : "/dev/input/js0";
  int fd = open(path, O_RDONLY | O_CLOEXEC);
  if (fd < 0) {
    fprintf(stderr, "cannot open %s: %s\n", path, strerror(errno));
    return 1;
  }

  char name[256] = {0};
  unsigned char axis_count = 0;
  unsigned char button_count = 0;
  __u8 axes[ABS_CNT] = {0};
  __u16 buttons[KEY_CNT - BTN_MISC] = {0};
  if (ioctl(fd, JSIOCGNAME(sizeof(name)), name) < 0 ||
      ioctl(fd, JSIOCGAXES, &axis_count) < 0 ||
      ioctl(fd, JSIOCGBUTTONS, &button_count) < 0 ||
      ioctl(fd, JSIOCGAXMAP, axes) < 0 ||
      ioctl(fd, JSIOCGBTNMAP, buttons) < 0) {
    fprintf(stderr, "cannot inspect %s: %s\n", path, strerror(errno));
    close(fd);
    return 1;
  }

  printf("device=%s\nname=%s\naxes=%u\nbuttons=%u\n", path, name, axis_count,
         button_count);
  for (unsigned int index = 0; index < axis_count; ++index) {
    const char *symbol = axis_name(axes[index]);
    printf("axis[%u]=%u%s%s\n", index, axes[index], symbol ? " " : "",
           symbol ? symbol : "");
  }
  for (unsigned int index = 0; index < button_count; ++index) {
    const char *symbol = button_name(buttons[index]);
    printf("button[%u]=%u%s%s\n", index, buttons[index], symbol ? " " : "",
           symbol ? symbol : "");
  }
  close(fd);
  return 0;
}
