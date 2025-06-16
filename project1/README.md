## High-Level Approach
* The program is designed such that the server starts and begins listening for connections first.
* The client then connects to the server to initiate communication.

## Challenges Faced
1. Logic for Guessing and Retrying:

* Ensuring the guess and retry functions worked correctly on both the client and server sides was challenging.
* Debugging the interaction between client.py and server.py required careful testing and refinement.

2. Guessing Strategy:

* Initially, I looped through the length of the guessed word, trying 26 different letters for each position and stopping when the mark was 2. However, this approach didn't verify if the guess was part of the word_list, which caused errors.
* The strategy had to be revised multiple times to ensure correctness.

## Guessing Strategy
* The revised strategy identifies the correct letter for each position based on feedback(marks) and checks the word_list for the first word where the letter at that position matches.
* If no such word is found, the function defaults to returning the first word in the word_list.

## How to Test the Code
1. Testing Communication:

* Added many print statements to verify that the client and server are correctly sending and receiving messages.

2. Testing the Guessing Strategy:

* Added print statements to check the letter in each position during the guessing process. This provided insight into how the strategy was working and helped refine the logic.