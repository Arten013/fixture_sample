# 実際のコードでは __init__.py に実装をあまり書かないようにしましょう


class ObjectWithDB:
    def connect(self):
        raise OSError("Hey, don't call me without db connection info!")
