tool_list = []
tool_handlers = {}


def register_tool(definition):
    def decorator(func):
        name = definition["name"]

        if name in tool_handlers:
            raise ValueError(f"工具名称重复：{name}")

        tool_list.append(definition)
        tool_handlers[name] = func

        return func

    return decorator

