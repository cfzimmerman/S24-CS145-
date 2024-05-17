PYTHON_PATH=$(which python3)
FOLDER=../RTP-opt
PORT_RECV=40000
PORT_SEND=50000
WINDOW_SIZE=128
ERROR_TYPE="0123"

# Kill previous ports first
sudo kill -9 $(sudo lsof -ti:$PORT_RECV,$PORT_SEND)

sudo $PYTHON_PATH $FOLDER/receiver.py $PORT_RECV $WINDOW_SIZE >output.txt &
RECEIVER_PID=$!
sleep 1

echo "Step 1: start the receiver with process id $RECEIVER_PID"

sudo $PYTHON_PATH proxy.py localhost $PORT_SEND localhost $PORT_RECV $ERROR_TYPE >/dev/null &
PROXY_PID=$!
sleep 1

echo "Step 2: start the proxy with process id $PROXY_PID"

# > /dev/null
sudo $PYTHON_PATH $FOLDER/sender.py localhost $PORT_SEND $WINDOW_SIZE <test_message.txt &
SENDER_PID=$!

echo "Step 3: start the sender with process id $SENDER_PID"

# Sleep 10 seconds for all finish
sleep 10

# Interrupt the receiver and proxy
sudo kill -INT $RECEIVER_PID $PROXY_PID $SENDER_ID

echo "Step 4: compare result"
bash compare.sh output.txt test_message.txt
