dir structure

filesystem/
├── navigation.py
│   ├── list_directory
│   ├── tree
│   ├── current_directory
│   ├── exists
│   ├── metadata
│
├── search.py
│   ├── find
│   ├── glob
│   └── search
│
├── files.py
│   ├── read_file
│   ├── write_file
│   ├── append_file
│   ├── read_multiple
│   └── create_file
│
└── operations.py
    ├── copy
    ├── move
    ├── rename
    ├── delete
    └── create_directory


from langchain.tools import tool

@tool
tools = [...,filesystemtools]
llm_with_tools = make_llm().bind_tools(tools)

function 

list_directory(path=".", recursive=False, show_hidden=False)

tree(path=".", max_depth=3, show_hidden=False)

read_file(path, encoding="utf-8")

read_multiple(paths, encoding="utf-8")

write_file(path, content, overwrite=True, encoding="utf-8")

append_file(path, content, encoding="utf-8")

create_file(path, exist_ok=False)

create_directory(path, parents=True, exist_ok=True)

copy(source, destination, overwrite=False)

move(source, destination, overwrite=False)

rename(path, new_name)

delete(path, recursive=False)

exists(path)

metadata(path)

search(path, pattern, case_sensitive=False)

find(pattern, root=".", recursive=True)

glob(pattern, root=".")

current_directory()