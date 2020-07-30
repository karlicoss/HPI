def messages():
    from . import vk_messages_backup as VMB
    yield from VMB.messages()
