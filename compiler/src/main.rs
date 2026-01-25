use std::{collections::HashMap, fs, io::Write};

use clap::Parser as ClapParser;
use pest::Parser;
use pest_derive::Parser;

#[derive(Parser)]
#[grammar = "grammar.pest"]
struct MyParser;

#[derive(ClapParser)]
#[command(name = "compiler")]
#[command(about = "Compiles LED controller assembly to binary")]
struct Args {
    /// Input assembly file
    input: String,

    /// Output raw binary file
    #[arg(long)]
    bin: Option<String>,

    /// Output hex text file (space-separated hex values)
    #[arg(long)]
    hex: Option<String>,
}

fn main() {
    let args = Args::parse();

    if args.bin.is_none() && args.hex.is_none() {
        eprintln!("error: at least one of --bin or --hex must be specified");
        std::process::exit(1);
    }

    let data = fs::read_to_string(&args.input).expect("failed to open file");
    let file = MyParser::parse(Rule::file, &data).expect("failed to parse");

    let mut labels = HashMap::new();

    let mut pc = 0u32;

    // extract all labels
    for line in file.clone() {
        for item in line.into_inner() {
            match item.as_rule() {
                Rule::label_define => {
                    let label = item.into_inner().as_str();
                    if labels.contains_key(label) {
                        panic!("label {} already defined", label);
                    }
                    labels.insert(label.to_owned(), pc);
                }
                Rule::instruction => {
                    pc += 2;
                }
                _ => {}
            }
        }
    }

    pc = 0;

    let mut program_buf = vec![];

    for line in file {
        for item in line.into_inner() {
            match item.as_rule() {
                Rule::label_define => {}
                Rule::instruction => {
                    let mut inner_rules = item.into_inner();

                    let name = inner_rules.next().expect("missing instruction").as_str();

                    let (opcode, operand) = match name {
                        "ldx" | "ldy" | "cpx" | "cpy" | "sty" | "stx" | "stall" | "beq" | "bne"
                        | "bmi" | "bpl" | "jmp" => {
                            let mut operand = inner_rules
                                .next()
                                .expect("operand required")
                                .into_inner()
                                .next()
                                .expect("missing inner operand");

                            let rule = operand.as_rule().clone();

                            let value = match rule {
                                Rule::immediate | Rule::register => {
                                    let mut item = operand.into_inner().next().unwrap();
                                    match item.as_rule() {
                                        Rule::decimal => item
                                            .as_str()
                                            .parse::<u32>()
                                            .expect("invalid integer literal"),
                                        Rule::hex => u32::from_str_radix(&item.as_str()[1..], 16)
                                            .expect("invalid integer literal"),
                                        r => panic!("invalid operand immediate type: {:?}", r),
                                    }
                                }
                                Rule::label => {
                                    let label = operand.as_str();
                                    let label_pc = *labels
                                        .get(label)
                                        .expect(&format!("missing label {}", label));
                                    label_pc
                                }
                                r => panic!("unsuported operand {:?}", r),
                            };

                            if value > 255 {
                                panic!("value {} out of range (0-255)", value);
                            }

                            let next_pc = pc + 2;
                            let branch_offset = if value > next_pc {
                                if value - next_pc > 127 {
                                    panic!("branch out of range: {} > 127", value - next_pc);
                                }
                                value - next_pc
                            } else if value < next_pc {
                                if next_pc - value > 128 {
                                    panic!("branch out of range: {} < -128", next_pc - value);
                                }
                                ((!(next_pc - value)).wrapping_add(1)) & 0b11111111
                            } else {
                                0
                            };

                            //println!("name {}, val: {:?}", name, value);

                            let opcode = match (name, rule) {
                                ("ldx", Rule::immediate) => 0b0001,
                                ("ldy", Rule::immediate) => 0b0010,
                                ("cpx", Rule::immediate) => 0b0011,
                                ("cpy", Rule::immediate) => 0b0100,
                                ("bne", Rule::immediate) => 0b0111,
                                ("bne", Rule::label) => 0b0111,
                                ("beq", Rule::immediate) => 0b1000,
                                ("beq", Rule::label) => 0b1000,
                                ("stall", Rule::immediate) => 0b1001,
                                ("ldx", Rule::register) => 0b1010,
                                ("ldy", Rule::register) => 0b1011,
                                ("cpx", Rule::register) => 0b1100,
                                ("cpy", Rule::register) => 0b1101,
                                ("sty", Rule::register) => 0b1110,
                                ("stx", Rule::register) => 0b1111,
                                ("jmp", Rule::label) => 0b10000,
                                ("bmi", Rule::label) => 0b10001,
                                ("bpl", Rule::label) => 0b10010,
                                r => panic!("invalid instruction: {:?}", r),
                            };

                            let operand = if rule == Rule::label && name != "jmp" {
                                branch_offset
                            } else {
                                value
                            };

                            (opcode, operand)
                        }
                        "nop" => (0b0000, 0),
                        "iny" => (0b0101, 0),
                        "inx" => (0b0110, 0),
                        "dey" => (0b10011, 0),
                        "dex" => (0b10100, 0),
                        _ => panic!("unsupported instruction: {}", name),
                    };

                    println!(
                        "{:02X}: {:?} ${:02x}\t\t\t; {:02x} {:02x}",
                        pc, name, operand, opcode, operand
                    );
                    pc += 2;

                    program_buf.extend(&[opcode, operand]);

                }
                Rule::EOI => {}
                r => panic!("unsupported rule: {:?}", r),
            }
        }
    }

    if program_buf.len() > 128 {
        panic!("max program size is 64 instructions");
    }

    // add nops
    for _ in 0..128 - program_buf.len() {
        program_buf.push(0);
    }

    if let Some(bin_path) = &args.bin {
        let mut bin_file = fs::File::create(bin_path).expect("failed to create bin file");
        bin_file
            .write_all(&program_buf.iter().map(|n| *n as u8).collect::<Vec<_>>())
            .unwrap();
    }

    if let Some(hex_path) = &args.hex {
        let mut hex_file = fs::File::create(hex_path).expect("failed to create hex file");
        hex_file
            .write_all(
                program_buf
                    .iter()
                    .map(|n| format!("{:02X}", *n))
                    .collect::<Vec<_>>()
                    .join(" ")
                    .as_bytes(),
            )
            .unwrap();
    }
}
