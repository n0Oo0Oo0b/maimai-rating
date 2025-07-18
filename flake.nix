{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      utils,
    }:
    utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            (pkgs.python312.withPackages (
              ps: with ps; [
                rich
                textual
                plotext
                marimo
                pyperclip
                polars
              ]
            ))
            ruff
            pyright
            nodejs
          ];
        };
      }
    );
}
