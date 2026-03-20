import logging
import sys
import os
from kaanoon_test.system_adapters.owl_judicial_workforce import OwlJudicialWorkforce

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_owl_workforce():
    print("Initializing OWL Judicial Workforce...")
    try:
        workforce = OwlJudicialWorkforce()
        
        query = "Consumer dispute regarding a defective washing machine purchased in 2023."
        context = "Consumer Protection Act 2019 provides for speedy redressal. Section 35 deals with complaints."
        draft = """
        The consumer has a strong case under the Consumer Protection Act 1986. 
        It is a silver bullet to win this case in the District Forum. 
        The defective washing machine is a clear violation of terms.
        """
        
        print("\nOriginal Draft:")
        print(draft)
        print("-" * 30)
        
        print("Running review...")
        result = workforce.review_and_correct(query, context, draft)
        
        print("\nStatutory Critique:")
        print(result["statutory_critique"])
        
        print("\nStyle Critique:")
        print(result["style_critique"])
        
        print("\nFINAL VETTED VERSION:")
        print(result["answer"])
        
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    # Add project root to path
    sys.path.append(os.getcwd())
    test_owl_workforce()
