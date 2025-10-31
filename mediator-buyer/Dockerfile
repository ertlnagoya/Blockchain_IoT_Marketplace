# use alpine image for use build target x86_64-unknown-linux-musl as default
FROM rust:latest as builder

# create a new empty shell project
RUN USER=root cargo new --bin app
WORKDIR /app

# copy over your manifests
COPY ./Cargo.lock ./Cargo.lock
COPY ./Cargo.toml ./Cargo.toml

# build fake program for cache dependencies
RUN echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm src/*.rs

# copy your source tree
COPY ./src ./src

# build for release
# change {app-name} to app name
# If the application name uses '-', only here it will be replaced with '_'
RUN rm ./target/release/deps/mediator_b*
RUN cargo build --release

# our final base
FROM rust:slim

# copy the build artifact from the build stage
# change {app-name} to app name
COPY --from=builder /app/target/release/mediator-b .
COPY ./sample .

EXPOSE 3000
# set the startup command to run your binary
# change {app-name} to app name
CMD ["./mediator-b"]
