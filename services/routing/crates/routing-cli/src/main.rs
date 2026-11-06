//! `routing` command-line tool. `spike` measures option B of ADR-003 (I0.8); the
//! `plan` subcommand arrives in increment I0.9.

use std::process::ExitCode;

mod plan;
mod spike;

const USAGE: &str = "usage: routing --version\n       routing plan --from <lat,lon|lieu> --to <lat,lon|lieu> --at <AAAA-MM-JJTHH:MM> --data <pack> [--virtual-spacing <m, 0 = sans>]\n       routing bench --data <pack> --pairs <couples.csv> --date <AAAA-MM-JJ> --out <mesures.json> [--times 06:30,11:00,18:30]\n       routing spike --gtfs <dossier> --pairs <couples.csv> --out <résultats.json> [--times 06:30,11:00,18:30] [--virtual-spacing <m>] [--simulated-waits <graine>] [--repeat <n>]";

/// Outcome of parsing the command-line arguments.
#[derive(Debug, PartialEq)]
enum Command {
    Version,
    Help,
    Spike(spike::SpikeArgs),
    Plan(plan::PlanArgs),
    Bench(plan::BenchArgs),
}

fn parse<I: IntoIterator<Item = String>>(args: I) -> Result<Command, String> {
    let args: Vec<String> = args.into_iter().collect();
    match args.as_slice() {
        [flag] if flag == "--version" || flag == "-V" => Ok(Command::Version),
        [] => Ok(Command::Help),
        [flag] if flag == "--help" || flag == "-h" => Ok(Command::Help),
        [command, rest @ ..] if command == "spike" => {
            spike::SpikeArgs::parse(rest).map(Command::Spike)
        }
        [command, rest @ ..] if command == "plan" => plan::PlanArgs::parse(rest).map(Command::Plan),
        [command, rest @ ..] if command == "bench" => {
            plan::BenchArgs::parse(rest).map(Command::Bench)
        }
        _ => Err(format!("unrecognised arguments: {}", args.join(" "))),
    }
}

fn main() -> ExitCode {
    match parse(std::env::args().skip(1)) {
        Ok(Command::Version) => {
            println!("routing {}", routing_core::version());
            ExitCode::SUCCESS
        }
        Ok(Command::Help) => {
            println!("{USAGE}");
            ExitCode::SUCCESS
        }
        Ok(Command::Plan(args)) => match plan::run_plan(&args) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("routing plan : {error}");
                ExitCode::FAILURE
            }
        },
        Ok(Command::Bench(args)) => match plan::run_bench(&args) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("routing bench : {error}");
                ExitCode::FAILURE
            }
        },
        Ok(Command::Spike(args)) => match spike::run(&args) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("routing spike : {error}");
                ExitCode::FAILURE
            }
        },
        Err(message) => {
            eprintln!("{message}\n{USAGE}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| (*value).to_owned()).collect()
    }

    #[test]
    fn parses_version_flags() {
        assert_eq!(parse(args(&["--version"])), Ok(Command::Version));
        assert_eq!(parse(args(&["-V"])), Ok(Command::Version));
    }

    #[test]
    fn shows_help_without_arguments() {
        assert_eq!(parse(args(&[])), Ok(Command::Help));
    }

    #[test]
    fn rejects_unknown_arguments() {
        assert!(parse(args(&["plan", "--from", "x"])).is_err());
    }
}
