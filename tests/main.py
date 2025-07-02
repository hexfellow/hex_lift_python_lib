import sys
sys.path.insert(1, '<Your project path>/hex_lift_python_lib')
sys.path.insert(1, '<Your project path>/hex_lift_python_lib/hex_lift/generated')

from hex_lift import PublicAPI as LiftAPI
import time

def main():
    # Init LiftAPI
    api = LiftAPI(ws_url = "ws://172.18.20.80:8439", control_hz = 100)

    # Get lift interface
    lift_interface = api.lift

    if lift_interface is None:
        print("Lift is not initialized.")
        exit(0)
    else:
        lift_interface.init_lift()

    try:
        while True:
            if api.is_api_exit():
                print("Public API has exited.")
                break
            else:
                data, count = api._get_raw_data()
                if data != None:
                    pass
                    # print("count = ", count)

                if lift_interface.has_new_data():
                    # get lift data
                    status = lift_interface.get_lift_status()
                    if status == 0:
                        print("Lift is LsBrake.")
                    elif status == 1:
                        print("Lift is LsCalibrating.")
                    elif status == 2:
                        print("Lift is LsAlgrithmControl.")
                    elif status == 3:
                        print("Lift is LsOvertakeControl.")
                    elif status == 4:
                        print("Lift is LsEmergencyStop.")
                    else:
                        print("Unexpected lift state.")

                    print("current_pos: ", lift_interface.get_current_pos())
                    print("max_speed: ", lift_interface.get_current_max_speed())
                    print("max_pos: ", lift_interface.get_max_pos())
                    print("error: ", lift_interface.get_error())
                    print("custom_button_pressed: ", lift_interface.get_custom_button_pressed())

                # set target pos
                try:
                    lift_interface.set_target_pos(-0.3)
                except Exception as e:
                    print("set_target_pos error: ", e)
                
                # # set max speed
                # try:
                #     lift_interface.set_max_speed(20000)
                # except Exception as e:
                #     print("set_max_speed error: ", e)
                
                # # set brake
                # try:
                #     lift_interface.set_brake(False)
                # except Exception as e:
                #     print("set_brake error: ", e)

            time.sleep(0.001)
            
    except KeyboardInterrupt:
        print("Received Ctrl-C.")
        api.close()
    finally:
        pass

    print("Resources have been cleaned up.")
    exit(0)

if __name__ == "__main__":
    main()