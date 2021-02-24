from irctest import cases


class ReadqTestCase(cases.BaseServerTestCase):
    """Test responses to DoS attacks using long lines."""

    @cases.mark_specifications("Oragono")
    def testReadqTags(self):
        self.connectClient("mallory", name="mallory", capabilities=["message-tags"])
        self.joinChannel("mallory", "#test")
        self.sendLine("mallory", "PRIVMSG #test " + "a" * 16384)
        self.assertDisconnected("mallory")

    @cases.mark_specifications("Oragono")
    def testReadqNoTags(self):
        self.connectClient("mallory", name="mallory")
        self.joinChannel("mallory", "#test")
        self.sendLine("mallory", "PRIVMSG #test " + "a" * 16384)
        self.assertDisconnected("mallory")
