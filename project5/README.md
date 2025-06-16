

### Challenge:
1) Difficult to test the program in small parts. Local testing worked, but integrating cookie management and status code logic caused issues. For example, In login(), had to ensure the POST request included username and password with proper formatting.

2) Encountered redirect loops with status codes 302 Found and 200 OK.

   * Solved by printing all requests and responses for debugging.

   * Discovered that including the port in the URL caused parsing failures for redirects (e.g., /).

3) Unexpected redirect to /logout. Solved with a simple condition to avoid following /logout links in the main crawler logic.




### Learned concpet:
* CSRF token:
Most login forms use a CSRF token to prevent cross-site request forgery. The server expects this token in the POST request when logging in.

* Cookies: 
    * Example format:
    i.e., Set-Cookie: sessionid=abc123; Path=/; HttpOnly; Secure
    
        - Used for identification, authentication, user tracking
        -  After login, the server sends a Set-Cookie header.
         - Store the session ID and include it in the Cookie header for future requests.


### Testing Strategy:
* Extensive use of print statements was essential for debugging.

* Printing raw requests and responses helped identify formatting issues and redirect problems.
