import json
import os


def combine_json_files():
    combined_records = []

    print("--- JSON Combiner Tool ---")
    print("Enter the absolute paths to your JSON files one by one.")
    print("Type 'done' and press Enter when you are finished.\n")

    # Step 1: Collect file paths from the user
    while True:
        user_input = input("Enter JSON file path (or 'done'): ").strip()

        # Clean up surrounding quotes if the user dragged and dropped the file into the console
        if (user_input.startswith('"') and user_input.endswith('"')) or (
            user_input.startswith("'") and user_input.endswith("'")
        ):
            user_input = user_input[1:-1]

        if user_input.lower() == "done":
            if not combined_records:
                print("No files were processed. Exiting.")
                return
            break

        # Validate file existence
        if not os.path.exists(user_input):
            print(f"❌ Error: File not found at '{user_input}'. Please try again.\n")
            continue

        # Step 2: Read and parse the current JSON file
        try:
            with open(user_input, "r", encoding="utf-8") as file:
                data = json.load(file)

                # Ensure the JSON fits the expected structure
                if "records" in data and isinstance(data["records"], list):
                    combined_records.extend(data["records"])
                    print(
                        f"✓ Successfully added {len(data['records'])} records.\n"
                    )
                else:
                    print(
                        "⚠️ Warning: File loaded, but it does not contain a top-level 'records' array. Skipped.\n"
                    )

        except json.JSONDecodeError:
            print(
                f"❌ Error: '{user_input}' is not a valid JSON file. Skipped.\n"
            )
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}\n")

    # Step 3: Package the combined data into the original structure
    output_data = {"records": combined_records}

    # Step 4: Save the combined output file
    output_filename = "combined_output.json"
    try:
        with open(output_filename, "w", encoding="utf-8") as outfile:
            json.dump(output_data, outfile, indent=2, ensure_ascii=False)

        print("--- Processing Complete ---")
        print(f"Successfully combined {len(combined_records)} total records!")
        print(f"Saved to: {os.path.abspath(output_filename)}")

    except Exception as e:
        print(f"❌ Failed to save the combined file: {e}")


if __name__ == "__main__":
    combine_json_files()