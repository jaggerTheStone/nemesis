//! `routing` command-line tool. The `plan` subcommand arrives in increment I0.9.

use std::process::ExitCode;

const USAGE: &str = "usage: routing --version";

/// Outcome of parsing the command-line arguments.
#[derive(Debug, PartialEq, Eq)]
enum Command {
    Version,
    Help,
}

fn parse<I: IntoIterator<Item = String>>(args: I) -> Result<Command, String> {
    let args: Vec<String> = args.into_iter().collect();
    match args.as_slice() {
        [flag] if flag == "--version" || flag == "-V" => Ok(Command::Version),
        [] => Ok(Command::Help),
        [flag] if flag == "--help" || flag == "-h" => Ok(Command::Help),
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
