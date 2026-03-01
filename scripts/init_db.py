"""本地初始化数据库表结构的脚本入口。"""

from app.core.database import init_db


if __name__ == "__main__":
    # 直接按当前配置创建全部表。
    init_db()
    print("database initialized")
