import json
import os


def lookup_json_records():
    print("--- JSON Record Lookup Tool ---")

    # Step 1: Get and validate Path A
    while True:
        path_a = (
            input("Enter path to JSON Object A (Records File): ")
            .strip()
            .strip('"')
            .strip("'")
        )
        if os.path.exists(path_a):
            break
        print("❌ File not found. Please enter a valid path.\n")

    # Step 2: Get and validate Path B
    while True:
        path_b = (
            input("Enter path to JSON Object B (Lookup Keys File): ")
            .strip()
            .strip('"')
            .strip("'")
        )
        if os.path.exists(path_b):
            break
        print("❌ File not found. Please enter a valid path.\n")

    # Step 3: Load and Parse Files
    try:
        with open(path_a, "r", encoding="utf-8") as f_a:
            data_a = json.load(f_a)

        with open(path_b, "r", encoding="utf-8") as f_b:
            data_b = json.load(f_b)

    except json.JSONDecodeError as e:
        print(f"\n❌ Error parsing JSON data: {e}")
        return
    except Exception as e:
        print(f"\n❌ An unexpected error occurred while reading: {e}")
        return

    # Step 4: Extract lookup keys from Object B into a Set for O(1) lookups
    print("\nProcessing lookup keys...")
    if not isinstance(data_b, list):
        print("❌ Error: Object B must be a top-level JSON Array/List.")
        return

    # We extract 'input_name', stripping whitespace to ensure clean matching
    lookup_keys = {
        item["input_name"].strip() for item in data_b if "input_name" in item
    }

    # Step 5: Filter Object A records based on the lookup set
    if "records" not in data_a or not isinstance(data_a["records"], list):
        print(
            "❌ Error: Object A does not contain a top-level 'records' array."
        )
        return

    matched_records = []
    for record in data_a["records"]:
        primary_alias = record.get("primary_alias", "").strip()

        # Check if the primary_alias exists in our Object B set
        if primary_alias in lookup_keys:
            matched_records.append(record)

    # Step 6: Save the filtered results
    output_data = {"records": matched_records}
    output_filename = "successful_lookups.json"

    try:
        with open(output_filename, "w", encoding="utf-8") as f_out:
            json.dump(output_data, f_out, indent=2, ensure_ascii=False)

        print("\n--- Match Complete ---")
        print(f"Total keys extracted from Object B: {len(lookup_keys)}")
        print(f"Successful matches found and kept: {len(matched_records)}")
        print(f"Saved matched output to: {os.path.abspath(output_filename)}")

    except Exception as e:
        print(f"❌ Failed to save output file: {e}")


if __name__ == "__main__":
    lookup_json_records()