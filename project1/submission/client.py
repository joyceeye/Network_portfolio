#!/usr/bin/env python3
"""client side"""
import socket
import argparse
import json
import urllib.request
import random
import ssl
import ast
import string

def get_words_from_server():
    """
    Get the word list from the server, ensuring proper formatting
    """
    url = "https://4700.network/projects/project1-words.txt"
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    with urllib.request.urlopen(url, context=context) as file:
        words = [line.decode('utf-8').strip() for line in file.readlines()]
    print("len:", len(words))
    return words

def make_guess(game_id, word):
    guess_object = {"type": "guess",
                "id": game_id, # start msg
                "word": word}
    guess_string = json.dumps(guess_object) + "\n"
    # print(f"guess message: {guess_string}") 
    return guess_string


def read_message(client):
    data = ""
    while "\n" not in data:
        chunk = client.recv(1024).decode()
        if not chunk:
            break
        data += chunk
    return data.strip()


alpha = chr(ord('a') - 1)
position = 0
results_guess = ''

def find_next_guess(previous_guess, previous_marks, word_list, tried_words=None):
    """
    Systematically tries letters in each position to find the secret word.
    Maintains correct positions (mark=2) once found.
    
    Args:
        previous_guess (str): The last word that was guessed, None if first guess
        previous_marks (list): List of marks from previous guess (0=wrong, 1=wrong position, 2=correct)
        word_list (list): List of valid words to choose from
        tried_words (set): Set of words already tried

    Returns:
        str: Next word to guess
    """
    global alpha
    global position
    global results_guess

    print("previous_marks", previous_marks)
    print("position", position)
    print("results_guess", results_guess)

    if previous_marks[position] == 2:
        alpha = chr(ord('a') - 1)
        results_guess += previous_guess[position]
        position += 1
    else:
        alpha = chr(ord(alpha) + 1)

    if len(results_guess) == 5:
        return results_guess

    for word in word_list:
        if word[position] == alpha:
            return word
        
    return word_list[0]


def logic_per_guess(hostname, port, username, use_tls=False):
    try:
        # create socket connection
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # client.settimeout(30)  # 30 second timeout

        # Setup TLS if requested
        if use_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            client = context.wrap_socket(client)

        client.connect((hostname, port))
        print("test for connection..")

        py_object = {"type": "hello", "northeastern_username": username}
        first_string = json.dumps(py_object) + "\n"
        print(f"sending the first message: {first_string}") 

        client.send(first_string.encode())
        print("send successfully")

        # first-time recv
        response = read_message(client)
        response_data = json.loads(response)
        print(f"message recived by the client is {response_data}")

        game_id = response_data["id"]
        word_list = get_words_from_server()
        previous_guess = word_list[0] 
        previous_marks = [0, 0, 0, 0, 0]
        attempts = 0
        
        # print(f"word list is {word_list}")
        while attempts < 500:
            guess_word = find_next_guess(previous_guess, previous_marks, word_list)
            print(f"guess_word = find_next_guess(previous_guess, previous_marks, word_list) is {guess_word}")
            guess_msg = make_guess(game_id, guess_word) # print guess message here!
            client.send(guess_msg.encode())

            response = read_message(client)
            response_data = json.loads(response)
            # print(f"1. response data: {response_data}")

            # situation 1: type => bye
            if response_data["type"] == "bye":
                flag = response_data["flag"]
                print(flag)
                print("the last bye...")
                client.close()
                return flag
            
            # situation 2: type => error
            elif response_data["type"] == "error":
                print("Programs encounter error!")
                client.close()
                return # terminate
            
            # increments the loop
            previous_guess = guess_word
            guess_data = response_data["guesses"]
            # print(f"guess_data: {guess_data}")
            previous_marks = guess_data[0]['marks']
            print(f"previous marks: {previous_marks}")

            # current msg
            # print("guess_data: ", guess_data[-1])
            # print(f"Word: {guess_data[0]['word']}, Marks: {guess_data[0]['marks']}") # in guess quotes: 0 
            
            attempts += 1

            if response_data["type"] == "retry":
                guess_data = response_data["guesses"]
                # print("guess_data: ", guess_data[0])
                # print(f"Word: {guess_data[0]['word']}, Marks: {guess_data['marks']}")
                continue  # Continue to next guess

        print(f"Reached {attempts} attempts without finding word, moving to next connection")
        return None  # Return None when max attempts reached
        
    finally:
        client.close()

# parse and encode
def main():
    # $ ./client <-p port> <-s> <hostname> <Northeastern-username>
    parser = argparse.ArgumentParser()

    parser.add_argument('-p','--port',type = int, help='the port number is:')
    parser.add_argument('-s', action = 'store_true', help='indicates TLS encryption')
    parser.add_argument('hostname', type=str, help='DNS name/IP addr')
    parser.add_argument('username', type=str, help='northeastern-username')

    args = parser.parse_args()
    # y = json.dumps(args)

    flags = []

    # Get regular flag
    port = args.port if args.port else 27993
    flag1 = logic_per_guess(args.hostname, port, args.username, False)
    flags.append(flag1)
    
    # Get TLS flag
    if args.s:
        port = args.port if args.port else 27994
        flag2 = logic_per_guess(args.hostname, port, args.username, True)
        flags.append(flag2)

    # Save both flags
    with open('secret_flags', 'w') as f:
        for flag in flags:
            f.write(f"{flag}\n")


if __name__ == "__main__":
    main()
