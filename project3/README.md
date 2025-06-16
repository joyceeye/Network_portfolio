** High-level approach:
1. Event-driven socket management: use select() to handle multiple connections simultaneously
2. Implement two table in this project:
    original_routes as router's memory of everything it's learned, while routing_table is the optimized representation used for making forwarding decisions.

    Be specific:

    - routing_table: works as the forwarding table
        - contains aggregated, optimized routes.
        - sent to peers when requesting a dump message.

    - original_routes(table): 
        - store unaggregated routes
        - keeps a route history for withdrawls


** Challenge:
1. Confusion between routing table and forwarding table:
    
    - The forwarding table should be populated when you receive route announcements (in handle_update). Each received update should add an entry to both:

        - routing_table (full BGP route information)
        - forwarding_table (simplified mapping of network/netmask to next hop)

2. Requirement Misinterpretation: Update Message Handling
    - Ensure forwarding legality before processing updates.
    - Implement can_forward check in handle_data.


3. Do the aggregation/ Disaggregation:
    -  Aggregation: 
        - Call before sending to the forwarding table.
        - Validate using prefix length and netmask.
 
    -  Disaggregation: 
        - Try to implement it as the reverse of aggregation, but always get an error in the message from the peer stating that it could not receive the route.
        - Re-read the aggregation part and find that the easiest way to fix it is to simply throw away the entire forwarding table and rebuild it.


** Testing Strategy:
1. Use each level of testing in the configuration package.
2. Check with print statements: "before aggregation..." / "after aggregation...".
