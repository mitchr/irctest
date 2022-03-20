import time

from irctest import cases, runner
from irctest.numerics import RPL_LIST, RPL_LISTEND, RPL_LISTSTART


class ListTestCase(cases.BaseServerTestCase):
    faketime = "+1y x60"  # for every wall clock second, 1 minute passed for the server

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testListEmpty(self):
        """<https://tools.ietf.org/html/rfc1459#section-4.2.6>
        <https://tools.ietf.org/html/rfc2812#section-3.2.6>
        <https://modern.ircdocs.horse/#list-message>
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.getMessages(1)
        self.sendLine(2, "LIST")
        m = self.getMessage(2)
        if m.command == RPL_LISTSTART:
            # skip
            m = self.getMessage(2)
        # skip local pseudo-channels listed by ngircd and ircu
        while m.command == RPL_LIST and m.params[1].startswith("&"):
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            RPL_LIST,
            "LIST response gives (at least) one channel, whereas there " "is none.",
        )
        self.assertMessageMatch(
            m,
            command=RPL_LISTEND,
            fail_msg="Second reply to LIST is not 322 (RPL_LIST) "
            "or 323 (RPL_LISTEND), or but: {msg}",
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testListOne(self):
        """When a channel exists, LIST should get it in a reply.
        <https://tools.ietf.org/html/rfc1459#section-4.2.6>
        <https://tools.ietf.org/html/rfc2812#section-3.2.6>

        <https://modern.ircdocs.horse/#list-message>
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)
        self.sendLine(2, "LIST")
        m = self.getMessage(2)
        if m.command == RPL_LISTSTART:
            # skip
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            RPL_LISTEND,
            fail_msg="LIST response ended (ie. 323, aka RPL_LISTEND) "
            "without listing any channel, whereas there is one.",
        )
        self.assertMessageMatch(
            m,
            command=RPL_LIST,
            fail_msg="Second reply to LIST is not 322 (RPL_LIST), "
            "nor 323 (RPL_LISTEND) but: {msg}",
        )
        m = self.getMessage(2)
        # skip local pseudo-channels listed by ngircd and ircu
        while m.command == RPL_LIST and m.params[1].startswith("&"):
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            RPL_LIST,
            fail_msg="LIST response gives (at least) two channels, "
            "whereas there is only one.",
        )
        self.assertMessageMatch(
            m,
            command=RPL_LISTEND,
            fail_msg="Third reply to LIST is not 322 (RPL_LIST) "
            "or 323 (RPL_LISTEND), or but: {msg}",
        )

    def _parseChanList(self, client):
        channels = set()
        while True:
            m = self.getMessage(client)
            if m.command == RPL_LISTEND:
                break
            if m.command == RPL_LIST:
                if m.params[1].startswith("&"):
                    # skip local pseudo-channels listed by ngircd and ircu
                    continue
                channels.add(m.params[1])

        return channels

    def _sleep_minutes(self, n):
        for _ in range(n):
            if self.controller.faketime_enabled:
                # From the server's point of view, 1 minute will pass
                time.sleep(1)
            else:
                time.sleep(60)

            # reply to pings
            self.getMessages(1)
            self.getMessages(2)

    @cases.mark_isupport("ELIST")
    @cases.mark_specifications("Modern")
    def testListCreationTime(self):
        """
        " C: Searching based on channel creation time, via the "C<val" and "C>val"
        modifiers to search for a channel creation time that is higher or lower
        than val."
        -- <https://modern.ircdocs.horse/#elist-parameter>
        -- https://datatracker.ietf.org/doc/html/draft-hardy-irc-isupport-00#section-4.8

        Unfortunately, this is ambiguous, because "val" is a time delta (in minutes),
        not a timestamp.

        On InspIRCd and Charybdis/Solanum, "C<val" is interpreted as "the channel was
        created less than <val> minutes ago

        On UnrealIRCd, Plexus, and Hybrid, it is interpreted as "the channel's creation
        time is a timestamp lower than <val> minutes ago" (ie. the exact opposite)
        """
        self.connectClient("foo")

        if "C" not in self.server_support.get("ELIST", ""):
            raise runner.OptionalExtensionNotSupported("ELIST=C")

        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan1")
        self.getMessages(1)

        # Helps debugging
        self.sendLine(1, "TIME")
        self.getMessages(1)

        self._sleep_minutes(2)

        # Helps debugging
        self.sendLine(1, "TIME")
        self.getMessages(1)

        self.sendLine(1, "JOIN #chan2")
        self.getMessages(1)

        self._sleep_minutes(1)

        self.sendLine(1, "LIST")
        self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})

        if self.controller.software_name in ("UnrealIRCd", "Plexus4", "Hybrid"):
            self.sendLine(2, "LIST C<2")
            self.assertEqual(self._parseChanList(2), {"#chan1"})

            self.sendLine(2, "LIST C>2")
            self.assertEqual(self._parseChanList(2), {"#chan2"})

            self.sendLine(2, "LIST C>0")
            self.assertEqual(self._parseChanList(2), set())

            self.sendLine(2, "LIST C<0")
            self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})

            self.sendLine(2, "LIST C>10")
            self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})
        elif self.controller.software_name in ("Solanum", "Charybdis", "InspIRCd"):
            self.sendLine(2, "LIST C>2")
            self.assertEqual(self._parseChanList(2), {"#chan1"})

            self.sendLine(2, "LIST C<2")
            self.assertEqual(self._parseChanList(2), {"#chan2"})

            self.sendLine(2, "LIST C<0")
            self.assertEqual(self._parseChanList(2), set())

            self.sendLine(2, "LIST C<0")
            self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})

            self.sendLine(2, "LIST C>10")
            self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})
        else:
            assert False, f"{self.controller.software_name} not supported"

    @cases.mark_isupport("ELIST")
    @cases.mark_specifications("Modern")
    def testListTopicTime(self):
        """
        "T: Searching based on topic time, via the "T<val" and "T>val"
        modifiers to search for a topic time that is lower or higher than
        val respectively."
        -- <https://modern.ircdocs.horse/#elist-parameter>
        -- https://datatracker.ietf.org/doc/html/draft-hardy-irc-isupport-00#section-4.8

        See testListCreationTime's docstring for comments on this.
        """
        self.connectClient("foo")

        if "T" not in self.server_support.get("ELIST", ""):
            raise runner.OptionalExtensionNotSupported("ELIST=T")

        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan1")
        self.sendLine(1, "JOIN #chan2")
        self.getMessages(1)

        self.sendLine(1, "TOPIC #chan1 :First channel")
        self.getMessages(1)

        # Helps debugging
        self.sendLine(1, "TIME")
        self.getMessages(1)

        self._sleep_minutes(2)

        # Helps debugging
        self.sendLine(1, "TIME")
        self.getMessages(1)

        self.sendLine(1, "TOPIC #chan2 :Second channel")
        self.getMessages(1)

        self._sleep_minutes(1)

        self.sendLine(1, "LIST")
        self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})

        if self.controller.software_name in ("UnrealIRCd", "Plexus4", "Hybrid"):
            self.sendLine(1, "LIST T>0")
            self.assertEqual(self._parseChanList(1), set())

            self.sendLine(1, "LIST T<0")
            self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})

            self.sendLine(1, "LIST T<2")
            self.assertEqual(self._parseChanList(1), {"#chan1"})

            self.sendLine(1, "LIST T>2")
            self.assertEqual(self._parseChanList(1), {"#chan2"})

            self.sendLine(1, "LIST T>10")
            self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})
        elif self.controller.software_name in ("Solanum", "Charybdis", "InspIRCd"):
            self.sendLine(1, "LIST T<0")
            self.assertEqual(self._parseChanList(1), set())

            self.sendLine(1, "LIST T>0")
            self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})

            self.sendLine(1, "LIST T>2")
            self.assertEqual(self._parseChanList(1), {"#chan1"})

            self.sendLine(1, "LIST T<2")
            self.assertEqual(self._parseChanList(1), {"#chan2"})

            self.sendLine(1, "LIST T<10")
            self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})
        else:
            assert False, f"{self.controller.software_name} not supported"
