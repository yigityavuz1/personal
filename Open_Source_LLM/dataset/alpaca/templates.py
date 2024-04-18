# templates for combining instructions, inputs for mistral chat template
alpaca_prompt_input_tr = [
    "{}\n\nTalimat: {} \nGirdi: {}",
    "{}\n\nTalimat: {} Girdi: {}",
    "{}\n\n{}\n{}",
    "{}\n\n{} \n{}",
    "{}\n\n{} {}",
    "{}\n\nTalimat: {} \nGirdi: {} \nÇıktı:"
]

alpaca_prompt_input_en = [
    "{}\n\nInstruction: {} \nInput: {}",
    "{}\n\nInstruction: {} Input: {}",
    "{}\n\nInstruction: {} \nInput: {} \nOutput:",
    "{}\n\n{}\n{}",
    "{}\n\n{} \n{}",
    "{}\n\n{} {}"
]
alpaca_prompt_no_input_tr = [
    "{}\n\nTalimat: {}",
    "{}\n\n{}",
    "{}\n\n{} \nÇıktı:",
    "{}\n\nTalimat: {} \nÇıktı:",
]

alpaca_prompt_no_input_en = [
    "{}\n\nInstruction: {}",
    "{}\n\n{}",
    "{}\n\n{} \nOutput:",
    "{}\n\nInstruction: {} \nOutput:"
]
