import os
import sys
from code_review.models import get_configured_model

def main():
    model = get_configured_model()
    print("Model:", model)
    
    if isinstance(model, str) or not hasattr(model, "generate"):
        print("Error: get_configured_model returned an invalid model.", file=sys.stderr)
        sys.exit(1)
        
    try:
        response = model.generate("hello hello can you reply with a single word yes")
        print("Response:", response.text)
    except Exception as e:
        print("Error:", repr(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
