import os
import subprocess
import json
import re
import openai


def extract_man_description(command):
    try:
        # Run man command and capture the output
        man_output = subprocess.run(['man', command], capture_output=True, text=True, check=True).stdout

        # Extract the DESCRIPTION section using regex
        description_match = re.search(r'DESCRIPTION\n(-+\n)?(.*?)\n\n', man_output, re.DOTALL)
        if description_match:
            description = description_match.group(2).strip()
            return description
        else:
            return f"No DESCRIPTION found for command '{command}'"
    except subprocess.CalledProcessError:
        return f"No man page found for command '{command}'"

def parse_man_options(command):
    try:
        # Run man command and capture the output
        man_output = subprocess.run(['man', command], capture_output=True, text=True, check=True).stdout

        # Extract options using regex
        options = re.findall(r'\n\s*(-\w|--\w[\w-]*)\s+(.*?)(\n\s*-|\n\n)', man_output, re.DOTALL)

        # Format options into a dictionary
        options_dict = {}
        for option in options:
            flag, description, _ = option
            options_dict[flag.strip()] = description.strip()

        return options_dict
    except subprocess.CalledProcessError:
        return {}

def build_tool_definition_from_man(command):
    description = extract_man_description(command)
    options = parse_man_options(command)

    # Generate a tool definition based on the description and options
    tool_definition = {
        "type": "function",
        "name": f"{command}_command",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
    }

    for option, desc in options.items():
        tool_definition["parameters"]["properties"][option] = {
            "type": "boolean" if desc.lower() in ["enable", "disable"] else "string",
            "description": desc
        }

    return tool_definition

def execute_command(command, args):
    cmd = [command]
    for key, value in args.items():
        if value is True or value == 'true':
            cmd.append(key)
        else:
            cmd.append(f"{key}={value}")
    print(cmd)

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def main():
    tool_definition = build_tool_definition_from_man("ls")

    client = openai.Client(api_key=os.getenv('OPENAI_API_KEY'))

    # Request ChatGPT to use the 'ls' command and get the current directory
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {"role": "user", "content": "list files sorted by name with human-readable file sizes"}
        ],
        functions=[tool_definition]
    )

    response_message = response.choices[0].message
    content = response_message.content or ""
    tool_calls = [response_message.function_call]

    if tool_calls:
        for tool_call in tool_calls:
            function_name = tool_call.name
            arguments = json.loads(tool_call.arguments)
            command = function_name.replace("_command", "")

            if function_name == f"{command}_command":
                output = execute_command(command, arguments)
                print(f"Output of '{command}':\n{output}")
    else:
        print(content)


if __name__ == "__main__":
    main()
