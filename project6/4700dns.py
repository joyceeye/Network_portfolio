#!/usr/bin/env -S python3 -u

import argparse, socket, time, json, select, struct, sys, math
from dnslib import DNSRecord, DNSHeader, RR, QTYPE, A, ZoneParser, RCODE
from collections import defaultdict
import threading
import queue

class Server:
    def __init__(self, root_ip, zone_path, port):
        self.root_ip = root_ip
        self.zone_path = zone_path
        self.ns_records = []
        self.root_server_ip = root_ip
        self.cache = {}
        self.cache_lock = threading.Lock()  # Lock for thread-safe cache access
        self.pending_queries = {}  # Track pending queries for timeouts
        self.pending_lock = threading.Lock()  # Lock for thread-safe pending queries

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("127.0.0.1", port))  # Bind to localhost
        self.port = self.socket.getsockname()[1]
        self.log("Bound to port %d" % self.port)

        self.record_map = defaultdict(list)  # used to extract the qname
        self.soa_domain = self.parse_zone_file(zone_path)  # parse the zone_file

    def log(self, message):
        sys.stderr.write(message + "\n")
        sys.stderr.flush() 

    def send(self, addr, message):
        self.log("Sending message:\n%s" % message)
        self.socket.sendto(message.pack(), addr)

    def recv(self, socket):
        data, addr = socket.recvfrom(65535)
        request = DNSRecord.parse(data)
        self.log("Received message from %s:\n%s" % (addr, request))
        
        # Process the request in a separate thread
        threading.Thread(target=self.process_request, args=(data, addr), daemon=True).start()
        return f"Processing request from {addr}"
    
    def process_request(self, data, addr):
        request = DNSRecord.parse(data)
        
        # Check if request has multiple questions (not supported)
        if len(request.questions) > 1:
            response = request.reply()
            response.header.rcode = RCODE.SERVFAIL
            self.send(addr, response)
            return
        
        qname = str(request.q.qname).rstrip(".")
        qtype = request.q.qtype
        
        # Check if recursion is desired
        recursion_desired = (request.header.rd == 1)
        if not recursion_desired and not self.is_authoritative_for(qname):
            # If recursion not desired and we're not authoritative, return SERVFAIL
            response = request.reply()
            response.header.rcode = RCODE.SERVFAIL
            self.send(addr, response)
            return
        
        response = request.reply()
        
        # Set initial flags
        response.header.ra = True  # Recursion available
        
        # Check if we're authoritative for this domain
        is_auth = self.is_authoritative_for(qname)
        
        if is_auth:
            # We're authoritative, serve from our records
            response = self.serve_authoritative(request, qname, qtype)
        else:
            # First check cache
            with self.cache_lock:
                cached_response = self.cache_lookup(qname, qtype)
            
            if cached_response:
                # Use cached response
                response = request.reply()
                for rr in cached_response.rr:
                    response.add_answer(rr)
                for rr in cached_response.auth:
                    response.add_auth(rr)
                for rr in cached_response.ar:
                    response.add_ar(rr)
                
                # Set recursion flags
                response.header.ra = True
            else:
                # Need to do recursive lookup
                response = self.recursive_query(request)
        
        self.send(addr, response)
    
    def is_authoritative_for(self, qname):
        """Check if we are authoritative for the given domain"""
        return qname == self.soa_domain or qname.endswith("." + self.soa_domain)
    
    def serve_authoritative(self, request, qname, qtype):
        """Serve records from our authoritative zone"""
        response = request.reply()
        found = False
        
        # Set authoritative flag
        response.header.aa = True
        
        # Check if we have the exact record requested
        if qname in self.record_map:
            for rr in self.record_map[qname]:
                if rr.rtype == qtype:
                    response.add_answer(rr)
                    found = True
        
        # Handle CNAME resolution
        if not found and qname in self.record_map:
            for rr in self.record_map[qname]:
                if rr.rtype == QTYPE.CNAME:
                    response.add_answer(rr)
                    found = True
                    cname_target = str(rr.rdata.label).rstrip(".")
                    
                    # Recursively resolve the CNAME target if it's in our zone
                    if cname_target in self.record_map:
                        for c_rr in self.record_map[cname_target]:
                            if c_rr.rtype == qtype:
                                response.add_answer(c_rr)
        
        # Add NS records to authority section
        if found and qtype != QTYPE.NS:
            for ns_rr in self.ns_records:
                response.add_auth(ns_rr)
        
        # Handle NS requests with glue records
        if qtype == QTYPE.NS and qname in self.record_map:
            for rr in self.record_map[qname]:
                if rr.rtype == QTYPE.NS:
                    response.add_answer(rr)
                    found = True
                    
                    # Add glue A records in ADDITIONAL section
                    ns_host = str(rr.rdata.label).rstrip(".")
                    if ns_host in self.record_map:
                        for glue_rr in self.record_map[ns_host]:
                            if glue_rr.rtype == QTYPE.A:
                                response.add_ar(glue_rr)
        
        # Handle NXDOMAIN for our authoritative zone
        if not found:
            response.header.rcode = RCODE.NXDOMAIN
            for rr in self.ns_records:
                response.add_auth(rr)
        
        return response
    
    def recursive_query(self, request):
        """Perform a recursive DNS lookup"""
        qname = str(request.q.qname).rstrip(".")
        qtype = request.q.qtype
        
        # Create initial response
        response = request.reply()
        
        # Perform the recursive lookup
        final_response = self.perform_recursive_lookup(request)
        
        if final_response:
            # Copy the results to our response
            response.header = final_response.header
            response.rr = final_response.rr
            response.auth = final_response.auth
            response.ar = final_response.ar
            
            # Override some flags
            response.header.id = request.header.id
            response.header.aa = False  # We're not authoritative
            response.header.ra = True   # Recursion available
        else:
            # Lookup failed
            response.header.rcode = RCODE.SERVFAIL
        
        return response
    
    def perform_recursive_lookup(self, request):
        """Actual recursive lookup implementation with retries"""
        qname = str(request.q.qname).rstrip(".")
        qtype = request.q.qtype
        
        # Start from the root server
        server_ip = self.root_server_ip
        server_port = 60053  # Root server port
        
        # We may need to make multiple queries
        remaining_steps = 20  # Limit the number of steps to avoid infinite loops
        
        # Track the current domain we're querying
        current_domain = qname
        
        while remaining_steps > 0:
            remaining_steps -= 1
            
            # Send the query to the current server
            response = self.send_query_with_retries(server_ip, server_port, request)
            
            if not response:
                # Server didn't respond after retries
                return None
            
            # Apply bailiwick checking
            response = self.bailiwick_check(current_domain, response)
            
            # Check if we got an answer
            if len(response.rr) > 0:
                # Cache the successful response
                with self.cache_lock:
                    self.cache_store(qname, qtype, response)
                return response
            
            # No answer yet, check for delegation
            ns_records = [rr for rr in response.auth if rr.rtype == QTYPE.NS]
            
            if not ns_records:
                # No delegation, return what we have
                return response
            
            # We have a delegation, get the next server
            next_server_found = False
            
            # Try to find a glue record first
            for ns_record in ns_records:
                ns_name = str(ns_record.rdata.label).rstrip(".")
                
                # Look for a matching A record in the additional section
                for ar in response.ar:
                    if ar.rtype == QTYPE.A and str(ar.rname).rstrip(".") == ns_name:
                        server_ip = str(ar.rdata)
                        current_domain = ns_name
                        next_server_found = True
                        break
                
                if next_server_found:
                    break
            
            # If no glue record, we need to resolve the NS name
            if not next_server_found and ns_records:
                ns_name = str(ns_records[0].rdata.label).rstrip(".")
                current_domain = ns_name
                
                # Create a new request for the NS name
                ns_request = DNSRecord.question(ns_name, "A")
                ns_request.header.rd = 1  # Set recursion desired
                
                # Recursively resolve the NS name
                ns_response = self.perform_recursive_lookup(ns_request)
                
                if ns_response and ns_response.rr:
                    for rr in ns_response.rr:
                        if rr.rtype == QTYPE.A:
                            server_ip = str(rr.rdata)
                            next_server_found = True
                            break
            
            if not next_server_found:
                # Could not find next server
                return response
            
            # Continue with the next server
            server_port = 60053  # Use 60053 for all DNS servers in this project
        
        # Exceeded maximum steps
        return response
    
    def send_query_with_retries(self, server_ip, server_port, request):
        """Send a DNS query with retries on timeout"""
        retry_count = 0
        max_retries = 5
        timeout = 1.0  # 1 second timeout
        
        while retry_count <= max_retries:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(timeout)
                
                self.log(f"Sending query to {server_ip}:{server_port} (attempt {retry_count+1})")
                sock.sendto(request.pack(), (server_ip, server_port))
                
                data, _ = sock.recvfrom(65535)
                sock.close()
                
                # Successfully received response
                return DNSRecord.parse(data)
                
            except socket.timeout:
                # Timed out, retry
                self.log(f"Query to {server_ip}:{server_port} timed out (attempt {retry_count+1})")
                retry_count += 1
                sock.close()
            
            except Exception as e:
                # Other error
                self.log(f"Error sending query to {server_ip}:{server_port}: {e}")
                sock.close()
                return None
        
        # All retries failed
        self.log(f"All retries to {server_ip}:{server_port} failed")
        return None
    
    def in_bailiwick(self, domain, rr_name):
        """Check if a record is within bailiwick of a domain"""
        rr_name = str(rr_name).rstrip(".")
        domain = str(domain).rstrip(".")
        
        # Record is within bailiwick if it's the domain itself or a subdomain
        return rr_name == domain or rr_name.endswith("." + domain)
    
    def bailiwick_check(self, domain, response):
        """Filter out records that are outside of bailiwick"""
        filtered_response = DNSRecord.parse(response.pack())  # Create a copy
        
        # Filter ANSWER section
        filtered_response.rr = [rr for rr in response.rr if self.in_bailiwick(domain, rr.rname)]
        
        # Filter AUTHORITY section
        filtered_response.auth = [rr for rr in response.auth if self.in_bailiwick(domain, rr.rname)]
        
        # Filter ADDITIONAL section
        filtered_response.ar = [rr for rr in response.ar if self.in_bailiwick(domain, rr.rname)]
        
        return filtered_response
    
    def cache_store(self, qname, qtype, response):
        """Store a response in the cache with proper TTL handling"""
        if response.header.rcode != RCODE.NOERROR or (len(response.rr) == 0 and len(response.auth) == 0):
            # Don't cache error responses or empty responses
            return
        
        # Find the minimum TTL from all records
        all_records = response.rr + response.auth + response.ar
        if not all_records:
            return
        
        min_ttl = min(rr.ttl for rr in all_records if rr.ttl > 0)
        if min_ttl <= 0:
            min_ttl = 60  # Default to 60 seconds if no valid TTL
        
        expire_time = time.time() + min_ttl
        
        # Store in cache
        key = (str(qname), qtype)
        self.cache[key] = (response, expire_time)
        
        # Schedule cache cleanup
        threading.Timer(min_ttl, self.purge_expired_cache_entries).start()
    
    def cache_lookup(self, qname, qtype):
        """Look up a response in the cache, respecting TTL"""
        key = (str(qname), qtype)
        if key in self.cache:
            response, expire_time = self.cache[key]
            
            if time.time() < expire_time:
                # Cache hit is still valid
                return response
            else:
                # Expired, remove from cache
                del self.cache[key]
        
        # Check for a CNAME entry in the cache
        key = (str(qname), QTYPE.CNAME)
        if key in self.cache:
            cname_response, expire_time = self.cache[key]
            
            if time.time() < expire_time:
                # Follow the CNAME chain
                for rr in cname_response.rr:
                    if rr.rtype == QTYPE.CNAME:
                        cname_target = str(rr.rdata.label).rstrip(".")
                        
                        # Look for the target record in cache
                        target_key = (cname_target, qtype)
                        if target_key in self.cache:
                            target_response, target_expire = self.cache[target_key]
                            
                            if time.time() < target_expire:
                                # Combine the responses
                                combined = cname_response.copy()
                                for target_rr in target_response.rr:
                                    combined.add_answer(target_rr)
                                return combined
        
        return None
    
    def purge_expired_cache_entries(self):
        """Remove expired entries from the cache"""
        now = time.time()
        with self.cache_lock:
            expired_keys = [k for k, (_, expire_time) in self.cache.items() if now >= expire_time]
            for k in expired_keys:
                del self.cache[k]
    
    def parse_zone_file(self, path):
        """Parse the zone file to get the Authoritative domain"""
        with open(path, 'r') as f:
            zone_text = f.read()
        
        soa_domain = None
        
        # Parse all records from the zone file
        zone_records = list(RR.fromZone(zone_text))
        for rr in zone_records:
            # Store the record in our record map
            self.record_map[str(rr.rname).rstrip('.')].append(rr)
            
            # Find the SOA record to determine our authoritative domain
            if rr.rtype == QTYPE.SOA and not soa_domain:
                soa_domain = str(rr.rname).rstrip('.')
                self.log(f"SOA: Authoritative for domain: {soa_domain}")
            
            # Keep track of NS records for our domain
            if rr.rtype == QTYPE.NS:
                self.ns_records.append(rr)
        
        return soa_domain

    def run(self):
        """Main server loop"""
        while True:
            # Use select to wait for incoming data without blocking
            socks = select.select([self.socket], [], [], 0.1)[0]
            for conn in socks:
                self.recv(conn)
                
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DNS Server')
    parser.add_argument('root_ip', type=str, help="The IP address of the root server")
    parser.add_argument('zone', type=str, help="The zone file for this server")
    parser.add_argument('--port', type=int, help="The port this server should bind to", default=0)
    
    args = parser.parse_args()
    server = Server(args.root_ip, args.zone, args.port)
    server.run()
