from model import load_model, generate
from config import MAX_NEW_TOKENS, TEMPERATURE, DO_SAMPLE

def main():
    model, tokenizer = load_model()

    print("\nPhi-3 Mini — type 'quit' to exit\n")
    while True:
        prompt = input("You: ").strip()
        if prompt.lower() in ("quit", "exit"):
            break
        if not prompt:
            continue

        response = generate(
            model, tokenizer, prompt,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            do_sample=DO_SAMPLE,
        )
        print(f"\nPhi-3: {response}\n")


if __name__ == "__main__":
    main()
