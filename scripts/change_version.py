import sys

def main():
    if len(sys.argv) > 0:
        module_name = sys.argv[1]
        lang_version = sys.argv[2]
    
        change_lang_version(module_name, lang_version)


def change_lang_version(module_name, lang_version):
    try:
        properties = dict()
        with open(f"{module_name}/gradle.properties", 'r') as config_file:
            for line in config_file:
                try:
                    name, value = line.split("=")
                    if "ballerinaLangVersion" in name:
                        value = lang_version + "\n"
                    properties[name] = value
                except ValueError:
                    continue
            config_file.close()

        with open(f"{module_name}/gradle.properties", 'w') as config_file:
            for prop in properties:
                config_file.write(prop + "=" + properties[prop])
            config_file.close()

    except FileNotFoundError:
        print(f"Cannot find the gradle.properties file for {module_name}")
        sys.exit(1)


main()
