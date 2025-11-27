from pydantic2ts import generate_typescript_defs

generate_typescript_defs("core/base/CRUD/schemas.py", "./coreBaseCRUDTypes.ts")