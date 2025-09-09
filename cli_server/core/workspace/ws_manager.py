from cli_server.common.utils.singleton import Singleton
from cli_server.core.workspace.workspace import WorkSpace

class WsManager(metaclass=Singleton):
    ws_list = {}
    active_ws = None
    active_id = None

    def __init__(self):
        self.ws_list={}
        self.active_ws = None
        self.active_id = None

    def setActive(self, id):
        print("setActive Entered")
        if self.ws_list and id in self.ws_list:
            self.active_ws = self.ws_list[id]
        else:
            temp_ws = WorkSpace()
            temp_ws.set('bts_id', id)
            self.ws_list[id] = temp_ws
            self.active_ws = temp_ws
        self.active_id = id
        return 'RESULT::OK'

    def getActive(self, id):
        if id in self.ws_list:
            return self.ws_list[id]

    def getBtsIp(self, id=None):
        if not id:
            id = self.active_id

        if id:
            ws =  self.ws_list[id]
            return ws.get('bts_ip')

    def set(self, key, val):
        if self.active_ws:
            self.active_ws.set(key,val)

        return 'RESULT::OK'

    def get(self, key):
        if self.active_ws:
            return self.active_ws.get(key)
        return 'RESULT::OK'

    def remove_ws(self, id):
        self.ws_list[id] = None
        return 'RESULT::OK'

def getWorkspace():
        return WsManager().active_ws