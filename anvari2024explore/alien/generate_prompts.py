import os
import sys
import pandas as pd
import jsonlines

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load data
script_dir = os.path.dirname(os.path.abspath(__file__))
file1 = os.path.join(script_dir, "alien_game_2023-04-28_out.csv")
file2 = os.path.join(script_dir, "alien_game_2023-06-02_out.csv")
df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)
df_all = pd.concat([df1, df2], ignore_index=True)

# Group the data by participant and session
# (each group = one experimental session)
groups = df_all.groupby(["participant.code", "session.code"])

# Fixed instructions text for the Alien Game task
instructions = (
    "In this task you create pictures by selecting and/or deselecting symbols presented in a row across 10 columns (see screenshot below).\n"
    "There are 10 different symbols and each row of symbols represents a picture. An alien from outer space likes to buy such pictures and it will pay different amounts for different pictures with different symbols, but you don't know what the alien likes and how the interconnectedness between the different symbols influences the payoff. Each block consists of 10 trials (a first example picture and its payoff are already displayed), and in every block you will face a different alien.\n\n"
    "On each trial you can combine symbols any way you like to make pictures: you can select or deselect as many symbols as you wish (0-10), but you must make a decision for every symbol in every trial as the alien considers the entire combination of selected and not-selected symbols. When you're ready you can click on the \"Submit\" button and the price will then be shown under the heading \"Payoff\" and the trial is completed.\n"
    "If you submit the same picture in the same block, you'll be paid the same price. At the end of each block, the alien buys all of the pictures you created in that block and pays you the accumulated price. The value of the pictures will change from one block to the next.\n\n"
    "The first block will be for practice, but the points you earn from the remaining 3 blocks will be used to determine your bonus payment for this task. For this task, you will be paid a bonus of 2 pence (£0.02) per 10 points.\n"
)

all_prompts = []

# Process each experimental session
for (participant_code, session_code), df_session in groups:
    # Sort trials by block and then by trial number
    df_session = df_session.sort_values(by=["block", "trial"])

    # Begin building the prompt text with the instructions
    prompt_text = instructions + "\n\n"

    # Process blocks (Block 1 = practice, Blocks 2+ = incentivized)
    blocks = sorted(df_session["block"].unique())
    for block in blocks:
        # Select data for the block and compute cumulative payoff
        df_block = df_session[df_session["block"] == block]
        cumulative_points = df_block["player.landscape_payoff"].cumsum().tolist()

        # Label block appropriately
        if block == 1:
            prompt_text += "Practice Block:\n\n"
        else:
            prompt_text += f"Incentivized Block {block - 1}:\n\n"

        # Iterate over trials in the block
        for i, (_, row) in enumerate(df_block.iterrows()):
            trial_num = int(row["trial"])
            payoff = row["player.landscape_payoff"]
            cumulative = cumulative_points[i]
            picture_config = row["player.nk_landscape"]

            # Build the trial description
            trial_line = (
                f"Trial {trial_num}: Picture configuration: <<{picture_config}>>. "
                f"Received {payoff} points. Total points: {cumulative}.\n"
            )
            prompt_text += trial_line

        prompt_text += "\n"

    prompt_text += "\nEnd of session.\n"

    # Create the prompt dictionary for the session
    prompt_dict = {
        "text": prompt_text,
        "experiment": "alien_game",
        "participant": participant_code,
        "session": session_code
    }

    all_prompts.append(prompt_dict)

# Write all prompts jsonl
output_file = os.path.join(script_dir, "prompts.jsonl")
with jsonlines.open(output_file, mode='w') as writer:
    writer.write_all(all_prompts)

print(f"Created {len(all_prompts)} prompt(s) in {output_file}.")
