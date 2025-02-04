from usvisa_scheduler import *

if __name__ == "__main__":
    req_count = 0
    first_loop = True
    change_city = True

    while True:
        try:
            change_city = not change_city
            update_city(change_city)

            if first_loop:
                t0 = time.time()
                req_count = 0
                start_process()
                first_loop = False

            req_count += 1
            print("-" * 60)
            print(f"Request count: {req_count}, Log time: {datetime.today()}")

            dates = get_date()

            if not dates:
                handle_no_dates()
            else:
                process_dates(dates)

                if schedule_if_possible(dates):
                    break

            if should_rest(t0):
                rest_program()
                first_loop = True
            else:
                retry_wait()

        except Exception as e:
            print(f"Exception occurred: {e}\nBreaking the loop!")
            #break