## High-Level Approach
* FTP operates using two sockets:
    * Control socket – Used to send FTP commands and receive responses (e.g., login, file request). This typically runs on port 21.
    * Data socket – Used to transfer actual file data. The port depends on whether active or passive mode is used.


## Challenges Faced
1. Argument parsing for the copy and remove operations. 
    * Initially,  I used the URL as the first argument and the path as the second to extract the host and other details.
    * Later, I restructured it to fit the required two-parameter command format:
    ./4700ftp [operation] [param1] [param2]
    * Carefully reading the requirements and structuring the logic accordingly saved time and improved overall clarity.

2. Command Handling: 
    * Managed multiple command levels and structured them effectively in the main function.


## How to Test the Code:
1. Testing Communication:
    * Added print statements to verify that the FTP server receives the correct response code.

2. Copy/Move Operations:
    * Tested target paths with URLs to ensure correct upload/download behavior.
