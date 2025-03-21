import os
import sys
import pandas as pd
import jsonlines

# Set project root if needed for imports (adjust path as necessary)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load data from CSV files (using low_memory=False to avoid dtype warnings)
script_dir = os.path.dirname(os.path.abspath(__file__))
file1 = os.path.join(script_dir, "observe_or_bet_2023-04-28_out.csv")
file2 = os.path.join(script_dir, "observe_or_bet_2023-06-02_out.csv")
df1 = pd.read_csv(file1, low_memory=False)
df2 = pd.read_csv(file2, low_memory=False)
df_all = pd.concat([df1, df2], ignore_index=True)

# Group the data by participant and session
groups = df_all.groupby(["participant.code", "session.code"])

# Fixed instructions text for the Observe or Bet Task
instructions = (
    "In this task, you'll see one light bulb on your screen and three buttons. "
    "On each trial you will click on one of the three buttons and then the light will turn on either blue or red, "
    "but you won't always see what colour it turns on. You'll only see what colour the light turns on if you choose the \"observe\" button. "
    "The light will have a higher probability of turning one colour than the other and this probability will remain the same throughout each block of trials "
    "but will change from one block to the next.\n\n"
    "Before each trial you can choose one of three actions by pressing one of the three buttons on the screen: \"guess blue\", \"guess red\", or \"observe\". "
    "If you choose to observe then you will be shown which colour the light turns on, but you won't get any points. "
    "If you guess either blue or red, then your guess will be recorded, but you won't be shown whether the guess was correct.\n\n"
    "For each correct guess you get 1 point and for each incorrect guess you lose 1 point. At the end of each block you'll get feedback about how many points you earned in that block.\n\n"
    "The first block will be for practice with only 25 trials, and the following 2 blocks will have 50 trials each and will be used to determine your bonus payment. "
    "You'll be paid a bonus of 4 pence (£0.04) per point.\n"
)

# Mapping from recorded selection values to the corresponding verbal action
action_mapping = {
    "bet_red": "guess red",
    "bet_blue": "guess blue",
    "observe": "observe"
}

all_prompts = []

# Process each experimental session
for (participant_code, session_code), df_session in groups:
    # Sort trials by block then by trial number
    df_session = df_session.sort_values(by=["block", "trial"])
    
    # Begin building the prompt text with the instructions
    prompt_text = instructions + "\n"
    
    # Iterate over each unique block in the session
    blocks = sorted(df_session["block"].unique())
    for block in blocks:
        df_block = df_session[df_session["block"] == block]
        
        # Label block: Block 1 is Practice; Blocks 2 and 3 are Incentivized (numbered 1 and 2)
        if block == 1:
            prompt_text += "Practice Block:\n\n"
        else:
            prompt_text += f"Incentivized Block {block - 1}:\n\n"
        
        # Iterate through trials in the block
        for i, (_, row) in enumerate(df_block.iterrows()):
            trial_num = int(row["trial"])
            recorded_action = row["player.selection"]
            # Map recorded action to the verbal action; default to recorded_action if no mapping exists.
            action = action_mapping.get(recorded_action, recorded_action)
            
            # Build trial description based on the action chosen
            if action == "observe":
                light_colour = row["player.light_colour"]
                trial_line = (
                    f"Trial {trial_num}: You chose to <<observe>> and observed that the light turned <<{light_colour}>>.\n"
                )
            else:
                trial_line = (
                    f"Trial {trial_num}: You chose to <<{action}>>.\n"
                )
            
            prompt_text += trial_line
        
        prompt_text += "\n"
    
    prompt_text += "End of session.\n"
    
    # Construct the prompt dictionary for the session
    prompt_dict = {
        "text": prompt_text,
        "experiment": "observe_or_bet",
        "participant": participant_code,
        "session": session_code
    }
    all_prompts.append(prompt_dict)

# Write all prompts to a JSONL file
output_file = os.path.join(script_dir, "prompts.jsonl")
with jsonlines.open(output_file, mode='w') as writer:
    writer.write_all(all_prompts)

print(f"Created {len(all_prompts)} prompt(s) in {output_file}.")
