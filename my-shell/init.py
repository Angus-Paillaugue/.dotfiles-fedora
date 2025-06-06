from services.config import APP_NAME
import os
from fabric.utils.helpers import exec_shell_command_async
import toml
import shutil

def deep_update(target: dict, update: dict) -> dict:
    """
    Recursively update a nested dictionary with values from another dictionary.
    Modifies target in-place.
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            # Si el valor es un diccionario y la clave ya existe en target como diccionario,
            # entonces actualiza recursivamente.
            deep_update(target[key], value)
        else:
            # De lo contrario, simplemente establece/sobrescribe el valor.
            target[key] = value
    return target  # Aunque modifica in-place, devolverlo es una convención común


def ensure_matugen_config():
    """
    Ensure that the matugen configuration file exists and is updated
    with the expected settings.
    """
    expected_config = {
        "config": {
            "reload_apps": True,
            "wallpaper": {
                "command": "swww",
                "arguments": [
                    "img",
                    "-t",
                    "outer",
                    "--transition-duration",
                    "1.5",
                    "--transition-step",
                    "255",
                    "--transition-fps",
                    "60",
                    "-f",
                    "Nearest",
                ],
                "set": True,
            },
            "custom_colors": {
                "red": {"color": "#FF0000", "blend": True},
                "green": {"color": "#00FF00", "blend": True},
                "yellow": {"color": "#FFFF00", "blend": True},
                "blue": {"color": "#0000FF", "blend": True},
                "magenta": {"color": "#FF00FF", "blend": True},
                "cyan": {"color": "#00FFFF", "blend": True},
                "white": {"color": "#FFFFFF", "blend": True},
            },
        },
        "templates": {
            "hyprland": {
                "input_path": f"~/.config/{APP_NAME}/config/matugen/templates/hyprland-colors.conf",
                "output_path": f"~/.config/{APP_NAME}/config/hypr/colors.conf",
            },
            f"{APP_NAME}": {
                "input_path": f"~/.config/{APP_NAME}/config/matugen/templates/{APP_NAME}.css",
                "output_path": f"~/.config/{APP_NAME}/styles/colors.css",
                "post_hook": f"fabric-cli exec {APP_NAME} 'app.apply_stylesheet()' &",
            },
            "kitty": {
                "input_path": '~/.config/my-shell/config/matugen/templates/kitty.conf',
                "output_path": '~/.config/kitty/colors.conf'
            }
        },
    }

    config_path = os.path.expanduser("~/.config/matugen/config.toml")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    existing_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                existing_config = toml.load(f)
            shutil.copyfile(config_path, config_path + ".bak")
        except toml.TomlDecodeError:
            print(
                f"Warning: Could not decode TOML from {config_path}. A new default config will be created."
            )
            existing_config = {}  # Resetear si está corrupto
        except Exception as e:
            print(f"Error reading or backing up {config_path}: {e}")
            # existing_config podría estar parcialmente cargado o vacío.
            # Continuar para intentar fusionar con defaults.

    # Usamos una copia de existing_config para deep_update si no queremos modificarlo directamente
    # o asegurarse que deep_update no lo haga si no es deseado.
    # La implementación actual de deep_update modifica 'target'.
    # Para ser más seguros, podemos pasar una copia si existing_config no debe cambiar.
    # merged_config = deep_update(existing_config.copy(), expected_config)
    # O si existing_config puede ser modificado:
    merged_config = deep_update(
        existing_config, expected_config
    )  # existing_config se modifica in-place

    try:
        with open(config_path, "w") as f:
            toml.dump(merged_config, f)
    except Exception as e:
        print(f"Error writing matugen config to {config_path}: {e}")

    current_wall = os.path.expanduser("~/.current.wall")
    hypr_colors = os.path.expanduser(f"~/.config/{APP_NAME}/config/hypr/colors.conf")
    css_colors = os.path.expanduser(f"~/.config/{APP_NAME}/styles/colors.css")

    if (
        not os.path.exists(current_wall)
        or not os.path.exists(hypr_colors)
        or not os.path.exists(css_colors)
    ):
        os.makedirs(os.path.dirname(hypr_colors), exist_ok=True)
        os.makedirs(os.path.dirname(css_colors), exist_ok=True)

        image_path = ""
        if not os.path.exists(current_wall):
            example_wallpaper_path = os.path.expanduser(
                f"~/.config/{APP_NAME}/assets/wallpapers_example/example-3.jpg"
            )
            if os.path.exists(example_wallpaper_path):
                try:
                    # Si ya existe (posiblemente un enlace roto o archivo regular), eliminar y re-enlazar
                    if os.path.lexists(
                        current_wall
                    ):  # lexists para no seguir el enlace si es uno
                        os.remove(current_wall)
                    os.symlink(example_wallpaper_path, current_wall)
                    image_path = example_wallpaper_path
                except Exception as e:
                    print(f"Error creating symlink for wallpaper: {e}")
        else:
            image_path = (
                os.path.realpath(current_wall)
                if os.path.islink(current_wall)
                else current_wall
            )

        if image_path and os.path.exists(image_path):
            print(f"Generating color theme from wallpaper: {image_path}")
            try:
                matugen_cmd = f"matugen image '{image_path}'"
                exec_shell_command_async(matugen_cmd)
                print("Matugen color theme generation initiated.")
            except FileNotFoundError:
                print("Error: matugen command not found. Please install matugen.")
            except Exception as e:
                print(f"Error initiating matugen: {e}")
        elif not image_path:
            print(
                "Warning: No wallpaper path determined to generate matugen theme from."
            )
        else:  # image_path existe pero el archivo no
            print(
                f"Warning: Wallpaper at {image_path} not found. Cannot generate matugen theme."
            )

def generate_hypr_overrides():
    contents = """
$fabricSend = fabric-cli exec my-shell

bind = $mainMod, COMMA, exec, $fabricSend 'wallpaper_manager.toggle()'
bind = $mainMod SHIFT, V, exec, $fabricSend 'clipboard_manager.toggle()'
"""
    location = os.path.expanduser(f"~/.config/{APP_NAME}/config/hypr/overrides.conf")
    if not os.path.exists(location):
        os.makedirs(os.path.dirname(location), exist_ok=True)
        with open(location, "w") as f:
            f.write(contents)
            print(f"Hypr overrides generated at {location}")

def generate_hypr_entrypoint():
    contents = f"""source = ~/.config/{APP_NAME}/config/hypr/overrides.conf"""
    location = os.path.expanduser(f"~/.config/hypr/hyprland.conf")
    if not os.path.exists(location):
        raise FileNotFoundError(
            f"Hyprland configuration file not found at {location}. Please ensure Hyprland is installed."
        )
    already_contains = False
    with open(location, "r") as f:
        if contents.strip() in f.read():
            already_contains = True
    if not already_contains:
        with open(location, "a") as f:
            f.write(contents + '\n')
            print(f"Hyprland entrypoint updated at {location}")

def generate_hyprlock_config():
    contents = "source = ~/.config/my-shell/config/hypr/colors.conf"
    location = os.path.expanduser(f"~/.config/hypr/hyprlock.conf")
    if not os.path.exists(location):
        raise FileNotFoundError(
            f"Hyprlock configuration file not found at {location}. Please ensure Hyprlock is installed."
        )

    already_contains = False
    with open(location, "r") as f:
        if contents.strip() in f.read():
            already_contains = True
    if not already_contains:
        with open(location, "r") as original_file:
            data = original_file.read()
        with open(location, "w") as modified_file:
            modified_file.write(contents + "\n" + data)
        print(f"Hyprlock configuration updated at {location}")


def update_kitty_config():
    contents = "include colors.conf"
    location = os.path.expanduser(f"~/.config/kitty/kitty.conf")
    if not os.path.exists(location):
        raise FileNotFoundError(
            f"Kitty configuration file not found at {location}. Please ensure kitty is installed."
        )

    already_contains = False
    with open(location, "r") as f:
        if contents.strip() in f.read():
            already_contains = True
    if not already_contains:
        with open(location, "r") as original_file:
            data = original_file.read()
        with open(location, "w") as modified_file:
            modified_file.write(contents + "\n" + data)
        print(f"Kitty configuration updated at {location}")


if __name__ == "__main__":
    ensure_matugen_config()
    generate_hypr_overrides()
    generate_hypr_entrypoint()
    generate_hyprlock_config()
    update_kitty_config()
