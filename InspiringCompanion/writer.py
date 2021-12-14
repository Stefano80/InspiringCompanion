from re import sub


def normalize_entity_name(word):
    word = sub('[^a-zA-Z_-]+', '', word).replace("_", " ").replace("-", " ")
    word = " ".join(split_camel_case(word))
    return word


def split_camel_case(word):
    return sub('([A-Z][a-z]+)', r' \1', sub('([A-Z]+)', r' \1', word)).split()


def compile_log(characters, scene_description, user_text):
    if len(characters) >= 1:
        participants = ", ".join(characters) + " heeded the adventure's call. "
    else:
        participants = ''
    return f"{participants}{scene_description} {user_text}"


def stick_messages_together(messages, ignore):
    user_text = ""

    count = 0
    for m in messages:
        count += 1
        if count == 1:
            current_author = m.author
            continue
        if m.author != current_author:
            break
        if m.content[0] in ignore:
            continue

        user_text = f"{m.content} {user_text}"

    return user_text
