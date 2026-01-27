try:
    import numpy
    import sentence_transformers
    with open("install_check.txt", "w") as f:
        f.write("Success")
except ImportError as e:
    with open("install_check.txt", "w") as f:
        f.write(f"Failed: {e}")
