print("Ready. Scan a barcode (Ctrl+C to quit).")

try:
    while True:
        code = input("Scan now: ")   # scanner types digits + Enter
        code = code.strip()
        print(f"Got barcode: [{code}]")
except KeyboardInterrupt:
    print("\nExiting.")
