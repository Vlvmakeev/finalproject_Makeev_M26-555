from datetime import datetime
import secrets
import datetime

from valutatrade_hub.core.models import User
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


def register_user(username: str, password: str) -> User:
    """
    Создает нового пользователя и пустой портфель
    :param username:
    :param password:
    :return: объект User
    :raises: если username существует; пароль менее 4=х символов
    """
    if not username or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4-х символов")

    settings = SettingsLoader()
    db = DatabaseManager()
    users_path = settings.get("USERS_FILE_PATH")
    portfolio_path = settings.get("PORTFOLIO_FILE_PATH")

    users_raw = db.read_json(users_path)
    if any(u["username"] == username for u in users_raw):
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    new_id = max((u["user_id"] for u in users_raw), default=0) + 1

    salt = secrets.token_hex(8)
    hashed = User._hash(username, salt)

    user = User(
        user_id=new_id,
        username=username,
        hashed_password=hashed,
        salt=salt,
        registration_date=datetime.now(),
    )

    users_raw.append(user.to_dict())
    db.write_json(users_path, users_raw)

    portfolios = db.read_json(portfolio_path)
    portfolios.append({"user_id": new_id, "wallets": {}})
    db.write_json(portfolio_path, portfolios)

    return user