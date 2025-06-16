** High-level approach
1） authoritative server for a specific domain
2) serve as a recursive resolver for a number of local clients
3) needs to handle non-responsive DNS servers by sending approp response to client requests
4) needs to check the integrity of every packet recv

** Lists of properties designed
1) change the RR object to a dictionary using library, then could retrieve the answer based on the qname
2) Glue_records: For the level 3 of the tests: needs the additional section - for A records after NS records
3) level 12/13: recursive lookups -> the clinet only asks once and wait; 
                                  -> the local dns resolver is doing the iterative work on behalf of the client
                                  (Root -> gTLD -> Authoritative)
** Test strategy
configs -> used to test dnsserver and send it queries
and also responds to clients
4) after implement the forward to root function and recursive function. i found issues with previous pass tests. like CNAME

** Functionality:
interpret packets
manage dns cache
check for certain errors

** Things needs to pay attention to:
UDP port binds to 60053
if request with mutiple questions -> SERVFAIL
server never exits


response formatting:
dnslib includes DNSRecord.reply to build a skeleton reply from an incoming query, and the DNSRecord.pack method for formatting the DNS response

** libraries learned: 
RR.fromZone(): returns a generator of resourceRecord objects. Each objects has several attributes
