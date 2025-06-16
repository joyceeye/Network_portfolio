### High-level approach:

Design a reliable datagram transport protocol over UDP to ensure in-order, error-free, and duplicate-free data delivery. Implement mechanisms for sequencing, acknowledgment, and retransmission to handle packet loss, duplication, corruption, and reordering. Develop both sender and receiver components:

* Receiver: Listens indefinitely, acknowledges received packets, detects missing or out-of-order data, and requests retransmissions when necessary.
* Sender: Segments and transmits the file, implements retransmission on timeout or negative acknowledgment, and ensures flow control.

### Challenge:
1. Level 3: Initially struggled with implementing a receiver window to handle out-of-order (OoO) packets. Later understood that OoO segments should be buffered, using sequence numbers (seq) to compare with expected_seq and ensure correct ordering. Also, updated sender logic to increase self.window_size to 4.

2. Level 5: Faced difficulties understanding data corruption. Implemented checksum verification but encountered recurring JSON parsing errors. Identified the issue as an unclear sender-receiver relationship. Added checksum generation at the sender and validation at the receiver.

5. Level 7: Improved congestion control, particularly for low-bandwidth scenarios, by refining the on_timeout() function.


### Key Features of Design
* Adaptive Retransmission Timeout (RTO): Set to 2 × RTT, ensuring the sender waits sufficiently before assuming packet loss.
* Checksum-Based Error Detection: Added checksum in messages to detect data corruption. Simple to implement and effective in identifying corrupted packets.


### Testing Strategy:
* The self.log function was useful in the first four test levels for debugging and understanding data flow.
Analyzing the configuration output helped in evaluating overall logic. 
* For example, in Level 5, seeing "Mangling corrupted msg" indicated that the checksum implementation was not functioning correctly.