import alembic.config
import os

os.chdir(r"C:\Users\MS-Fin-10\Documents\GitHub\Digital-Arena")
alembicArgs = [
    '--raiseerr',
    'upgrade', 'head',
]
alembic.config.main(argv=alembicArgs)
print("✅ Migrations applied successfully!")
