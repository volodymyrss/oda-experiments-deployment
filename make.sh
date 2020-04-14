kubectl create secret generic db-user-pass  --from-file=./private/password.txt
kubectl create secret generic odatests-tests-bot-password  --from-file=./private/testbot-password.txt
kubectl create secret generic odatests-secret-key  --from-file=./private/secret-key.txt
