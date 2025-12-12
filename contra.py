import bcrypt

# Generar hash para la contraseña del admin
password = "AdminSeguro2025!"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print("Hash para admin:", hashed.decode('utf-8'))