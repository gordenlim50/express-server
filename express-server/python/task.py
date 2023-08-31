import sched
import time
import subprocess
   
def task():
    # Run the other script
    subprocess.run(["python", "lightsensor_mlv.py"])
    

current_time = time.time()
scheduler = sched.scheduler(time.time, time.sleep)
minutes = 1
delay_seconds = minutes*60

while 1:
    # Creates an instance of the scheduler class
    scheduler = sched.scheduler(time.time, time.sleep)

    scheduler.enterabs(current_time+delay_seconds, 1, task)

    # Run all scheduled events
    scheduler.run()

    # update current time
    current_time = time.time()
    