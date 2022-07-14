#!/usr/bin/env python3
import os 
import argparse
import re
import json
from collections import defaultdict

def count_votes( poll_id, max_votes_allowed: int = -1):

    regex = r"option_[0-9][0-9]*"
    pattern = re.compile(regex)
    search_directory = f"/opt/sw/poll/{poll_id}/results/" # TODO: 

    votes = defaultdict(int)
    for vote in os.listdir(search_directory): 
        vote_dir = os.path.join(search_directory, vote)
        with open(vote_dir, "r") as file :

            file_contents = file.read()
            marked_options = pattern.findall(file_contents)

            if max_votes_allowed >= len(marked_options): 
                for option in marked_options:
                    votes[option] += 1
    return json.dumps(dict(votes))

if __name__ == "__main__":
    parser =argparse.ArgumentParser()
    parser.add_argument("id", type=str, help="id of the poll")
    parser.add_argument("max_options", type=int, help="Maximum number of votes that user can use")
    args = parser.parse_args()
    print(count_votes(args.id, args.max_options))