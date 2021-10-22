#!/bin/bash

url='http://127.0.0.1:5000'

echo -e "\n=== manager ===\n"

echo "Adding a voting"
voting_id=$(
curl -s -X PUT $url/voting \
        -H 'Content-Type: application/json' \
        --data '
        {
            "name": "Który kot najlepszy",
            "options": [ "Kotowski", "czarny" ],
            "choiceType": "single-choice",
            "visibility": "open",
            "recipients": [
                "test1@baraniecki.eu",
                "test2@baraniecki.eu"
            ],
            "closesOnDate": "2025-01-02T03:01:45+01:00"
        }' \
    | jq '.votingId'
)



echo "Added voting (id=$voting_id):"
curl -s $url/votings | jq ".[] | select(.id == $voting_id)"

echo "Schedule:"
curl -s "$url/schedule?voting_id=$voting_id"

echo "Sending to first"
curl -s $url/schedule  -H 'Content-Type: application/json' --data '
    {
        "votingId": '$voting_id',
        "scheduleToSendOut": ["test1@baraniecki.eu"]
    }'

echo "Schedule:"
curl -s $url/schedule"?voting_id=$voting_id"

token=$(sqlite3 database.db "select token from tokens where voting_id=$voting_id")
echo "Token of first: $token"

echo "Sending to all"
curl -s $url/scheduleAllNotScheduled  -H 'Content-Type: application/json' --data '
    {
        "votingId": '$voting_id'
    }'

echo "Schedule:"
curl -s "$url/schedule?voting_id=$voting_id"

echo -e "\n=== client ===\n"

echo "Voting info:"
curl -s "$url/voting?token=$token"

echo "Casting a vote"
curl -s $url/vote -H 'Content-Type: application/json' --data '
    {
        "token": "'"$token"'",
        "choices": {
            "Kotowski": "for",
            "czarny": "against"
        }
    }'

echo "Trying to cast a vote when already cast: $(
    curl -s $url/vote -H 'Content-Type: application/json' --data '
        {
            "token": "'"$token"'",
            "choices": {
                "Kotowski": "for",
                "czarny": "against"
            }
    }')"

echo "Trying to get voting page info when vote already cast: $(
    curl -s $url/voting"?token=$token")"


echo -e "\n=== back to manager ===\n"

echo "Deleting the voting"
curl -X DELETE -s "$url/voting?voting_id=$voting_id"

echo "Searching for the deleted voting"
curl -s $url/votings | jq ".[] | select(.id == $voting_id)"
