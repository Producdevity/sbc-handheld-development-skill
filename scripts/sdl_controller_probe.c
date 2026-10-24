#include <SDL.h>

#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct options {
  int index;
  bool index_set;
  int watch_ms;
  const char *name;
  const char *guid;
  const char *mapping_file;
};

static int parse_nonnegative(const char *text, const char *name) {
  char *end = NULL;
  errno = 0;
  long value = strtol(text, &end, 10);
  if (errno != 0 || end == text || *end != '\0' || value < 0 ||
      value > 3600000) {
    fprintf(stderr, "%s must be between 0 and 3600000\n", name);
    exit(2);
  }
  return (int)value;
}

static struct options parse_options(int argc, char **argv) {
  struct options result = {.index = 0};
  for (int index = 1; index < argc; ++index) {
    if (strcmp(argv[index], "--help") == 0) {
      printf("usage: %s [--index N | [--name TEXT] [--guid GUID]] "
             "[--mapping-file PATH] [--watch-ms N]\n",
             argv[0]);
      exit(0);
    }
    bool is_index = strcmp(argv[index], "--index") == 0;
    bool is_watch = strcmp(argv[index], "--watch-ms") == 0;
    bool is_name = strcmp(argv[index], "--name") == 0;
    bool is_guid = strcmp(argv[index], "--guid") == 0;
    bool is_mapping = strcmp(argv[index], "--mapping-file") == 0;
    if (!is_index && !is_watch && !is_name && !is_guid && !is_mapping) {
      fprintf(stderr, "unknown option: %s\n", argv[index]);
      exit(2);
    }
    if (index + 1 >= argc) {
      fprintf(stderr, "missing value for %s\n", argv[index]);
      exit(2);
    }
    const char *value = argv[++index];
    if (is_index || is_watch) {
      int number =
          parse_nonnegative(value, is_index ? "--index" : "--watch-ms");
      if (is_index) {
        result.index = number;
        result.index_set = true;
      } else {
        result.watch_ms = number;
      }
    } else if (is_name) {
      result.name = value;
    } else if (is_guid) {
      result.guid = value;
    } else {
      result.mapping_file = value;
    }
  }
  if (result.index_set && (result.name || result.guid)) {
    fprintf(stderr, "--index cannot be combined with --name or --guid\n");
    exit(2);
  }
  return result;
}

static void device_guid(int index, char *buffer, size_t size) {
  SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(index), buffer,
                            (int)size);
}

static int device_matches(int index, const struct options *options) {
  char guid[64];
  const char *name = SDL_JoystickNameForIndex(index);
  device_guid(index, guid, sizeof(guid));
  if (options->name && (!name || !strstr(name, options->name))) {
    return 0;
  }
  if (options->guid && strcmp(guid, options->guid) != 0) {
    return 0;
  }
  return 1;
}

static int selected_index(const struct options *options) {
  int count = SDL_NumJoysticks();
  if (options->index_set || (!options->name && !options->guid)) {
    return options->index < count ? options->index : -1;
  }
  int selected = -1;
  for (int index = 0; index < count; ++index) {
    if (!device_matches(index, options)) {
      continue;
    }
    if (selected >= 0) {
      fprintf(stderr, "device selector matched more than one joystick\n");
      return -2;
    }
    selected = index;
  }
  return selected;
}

static void print_devices(void) {
  int count = SDL_NumJoysticks();
  printf("joysticks=%d\n", count);
  for (int index = 0; index < count; ++index) {
    char guid[64];
    const char *name = SDL_JoystickNameForIndex(index);
    int is_controller = SDL_IsGameController(index);
    device_guid(index, guid, sizeof(guid));
    printf("device[%d].name=%s\n", index, name ? name : "");
    printf("device[%d].guid=%s\n", index, guid);
    printf("device[%d].controller=%d\n", index, is_controller);
    SDL_GameController *controller =
        is_controller ? SDL_GameControllerOpen(index) : NULL;
    SDL_Joystick *joystick =
        controller ? SDL_GameControllerGetJoystick(controller)
                   : SDL_JoystickOpen(index);
    if (joystick) {
      printf("device[%d].instance=%d\n", index,
             SDL_JoystickInstanceID(joystick));
      printf("device[%d].axes=%d\n", index, SDL_JoystickNumAxes(joystick));
      printf("device[%d].buttons=%d\n", index,
             SDL_JoystickNumButtons(joystick));
      printf("device[%d].hats=%d\n", index, SDL_JoystickNumHats(joystick));
      printf("device[%d].balls=%d\n", index, SDL_JoystickNumBalls(joystick));
    } else {
      printf("device[%d].open_error=%s\n", index, SDL_GetError());
    }
    char *mapping = controller ? SDL_GameControllerMapping(controller) : NULL;
    printf("device[%d].mapping=%s\n", index, mapping ? mapping : "");
    SDL_free(mapping);
    if (controller) {
      SDL_GameControllerClose(controller);
    } else if (joystick) {
      SDL_JoystickClose(joystick);
    }
  }
}

static void print_event(const SDL_Event *event) {
  switch (event->type) {
  case SDL_CONTROLLERBUTTONDOWN:
  case SDL_CONTROLLERBUTTONUP: {
    const char *name =
        SDL_GameControllerGetStringForButton(event->cbutton.button);
    printf("button timestamp=%u instance=%d name=%s state=%s\n",
           event->cbutton.timestamp, event->cbutton.which,
           name ? name : "unknown",
           event->type == SDL_CONTROLLERBUTTONDOWN ? "down" : "up");
    break;
  }
  case SDL_CONTROLLERAXISMOTION: {
    const char *name = SDL_GameControllerGetStringForAxis(event->caxis.axis);
    printf("axis timestamp=%u instance=%d name=%s value=%d\n",
           event->caxis.timestamp, event->caxis.which, name ? name : "unknown",
           event->caxis.value);
    break;
  }
  case SDL_CONTROLLERDEVICEADDED:
    printf("controller-added timestamp=%u index=%d\n", event->cdevice.timestamp,
           event->cdevice.which);
    break;
  case SDL_CONTROLLERDEVICEREMOVED:
    printf("controller-removed timestamp=%u instance=%d\n",
           event->cdevice.timestamp, event->cdevice.which);
    break;
  case SDL_CONTROLLERDEVICEREMAPPED:
    printf("controller-remapped timestamp=%u instance=%d\n",
           event->cdevice.timestamp, event->cdevice.which);
    break;
  case SDL_JOYBUTTONDOWN:
  case SDL_JOYBUTTONUP:
    printf("raw-button timestamp=%u instance=%d index=%u state=%s\n",
           event->jbutton.timestamp, event->jbutton.which,
           event->jbutton.button,
           event->type == SDL_JOYBUTTONDOWN ? "down" : "up");
    break;
  case SDL_JOYAXISMOTION:
    printf("raw-axis timestamp=%u instance=%d index=%u value=%d\n",
           event->jaxis.timestamp, event->jaxis.which, event->jaxis.axis,
           event->jaxis.value);
    break;
  case SDL_JOYHATMOTION:
    printf("raw-hat timestamp=%u instance=%d index=%u value=0x%02x\n",
           event->jhat.timestamp, event->jhat.which, event->jhat.hat,
           event->jhat.value);
    break;
  case SDL_JOYDEVICEADDED:
    printf("joystick-added timestamp=%u index=%d\n", event->jdevice.timestamp,
           event->jdevice.which);
    break;
  case SDL_JOYDEVICEREMOVED:
    printf("joystick-removed timestamp=%u instance=%d\n",
           event->jdevice.timestamp, event->jdevice.which);
    break;
  }
  fflush(stdout);
}

int main(int argc, char **argv) {
  struct options options = parse_options(argc, argv);
  if (SDL_Init(SDL_INIT_GAMECONTROLLER | SDL_INIT_JOYSTICK | SDL_INIT_EVENTS) <
      0) {
    fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
    return 1;
  }
  SDL_version linked;
  SDL_GetVersion(&linked);
  printf("sdl=%u.%u.%u\n", linked.major, linked.minor, linked.patch);
  printf("mapping_file_env=%s\n",
         getenv("SDL_GAMECONTROLLERCONFIG_FILE")
             ? getenv("SDL_GAMECONTROLLERCONFIG_FILE")
             : "");
  printf("mapping_env=%s\n",
         getenv("SDL_GAMECONTROLLERCONFIG") ? "set" : "unset");
  if (options.mapping_file) {
    int added = SDL_GameControllerAddMappingsFromFile(options.mapping_file);
    if (added < 0) {
      fprintf(stderr, "cannot load mapping file %s: %s\n",
              options.mapping_file, SDL_GetError());
      SDL_Quit();
      return 1;
    }
    printf("mapping_file_added=%d\n", added);
  }
  print_devices();

  SDL_GameController *controller = NULL;
  SDL_Joystick *joystick = NULL;
  if (options.watch_ms > 0) {
    int index = selected_index(&options);
    if (index < 0) {
      fprintf(stderr, "%s\n", index == -2 ? "ambiguous device selector"
                                           : "selected joystick not found");
      SDL_Quit();
      return 1;
    }
    if (SDL_IsGameController(index)) {
      controller = SDL_GameControllerOpen(index);
      joystick =
          controller ? SDL_GameControllerGetJoystick(controller) : NULL;
    } else {
      joystick = SDL_JoystickOpen(index);
    }
    if (!joystick) {
      fprintf(stderr, "cannot open joystick %d: %s\n", index,
              SDL_GetError());
      SDL_Quit();
      return 1;
    }
    printf("watching_index=%d\n", index);
    Uint32 deadline = SDL_GetTicks() + (Uint32)options.watch_ms;
    while ((Sint32)(deadline - SDL_GetTicks()) > 0) {
      SDL_Event event;
      while (SDL_PollEvent(&event)) {
        print_event(&event);
      }
      SDL_Delay(2);
    }
  }

  if (controller) {
    SDL_GameControllerClose(controller);
  } else if (joystick) {
    SDL_JoystickClose(joystick);
  }
  SDL_Quit();
  return 0;
}
