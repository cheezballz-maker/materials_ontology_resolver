import json
import os
import sys
from pathlib import Path

def process_jsonl_file(input_path):
    """
    Process a JSONL file and extract specified fields.
    
    Args:
        input_path: Path to the input JSONL file
    
    Returns:
        Path to the output file
    """
    # Convert to Path object for easier manipulation
    input_path = Path(input_path)
    
    # Check if input file exists
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Create output filename
    stem = input_path.stem
    output_filename = f"{stem}_processed.jsonl"
    output_path = input_path.parent / output_filename
    
    # Fields to extract
    fields_to_extract = ['candidate', 'candidate_type', 'unique_name_count', 'example_normalized_names']
    
    # Process the file
    processed_count = 0
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            try:
                # Parse JSON line
                data = json.loads(line)
                
                # Extract only the desired fields
                extracted_data = {field: data.get(field) for field in fields_to_extract}
                
                # Write to output file
                outfile.write(json.dumps(extracted_data) + '\n')
                processed_count += 1
                
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse line {line_num}: {e}")
                continue
    
    print(f"Processed {processed_count} records")
    print(f"Output saved to: {output_path}")
    
    return output_path

def main():
    # Check if file path is provided as command line argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_jsonl_file>")
        print("Example: python script.py data/input.jsonl")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    try:
        output_file = process_jsonl_file(input_file)
        print(f"Successfully created: {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()