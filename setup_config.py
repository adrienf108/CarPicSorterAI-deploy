import tkinter as tk
from tkinter import messagebox

def save_config():
    with open('.env', 'w') as f:
        f.write(f'ANTHROPIC_API_KEY={api_key.get()}\n')
        f.write(f'PGUSER={db_user.get()}\n')
        f.write(f'PGPASSWORD={db_pass.get()}\n')
        f.write(f'PGDATABASE={db_name.get()}\n')
        f.write('PGHOST=localhost\n')
        f.write('PGPORT=5432\n')
        f.write(f'DATABASE_URL=postgresql://{db_user.get()}:{db_pass.get()}@localhost:5432/{db_name.get()}\n')
    
    messagebox.showinfo("Success", "Configuration saved!")
    root.quit()

root = tk.Tk()
root.title("Car Image Sorter Setup")

# Create labels and entry fields
tk.Label(root, text="Anthropic API Key:").grid(row=0)
tk.Label(root, text="Database Username:").grid(row=1)
tk.Label(root, text="Database Password:").grid(row=2)
tk.Label(root, text="Database Name:").grid(row=3)

api_key = tk.Entry(root, width=50)
db_user = tk.Entry(root)
db_pass = tk.Entry(root, show="*")
db_name = tk.Entry(root)

api_key.grid(row=0, column=1)
db_user.grid(row=1, column=1)
db_pass.grid(row=2, column=1)
db_name.grid(row=3, column=1)

tk.Button(root, text="Save", command=save_config).grid(row=4, column=1)

root.mainloop() 