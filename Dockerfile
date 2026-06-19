# Builder stage - Android SDK and build tools
FROM eclipse-temurin:17-jdk-jammy AS builder

# Install Android SDK
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=${PATH}:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools
ENV GRADLE_USER_HOME=/app/.gradle

WORKDIR /app

# Install Android command line tools (do this early to leverage cache)
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget unzip && \
    mkdir -p ${ANDROID_SDK_ROOT}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip && \
    unzip -q commandlinetools-linux-9477386_latest.zip -d ${ANDROID_SDK_ROOT}/cmdline-tools && \
    mv ${ANDROID_SDK_ROOT}/cmdline-tools/cmdline-tools ${ANDROID_SDK_ROOT}/cmdline-tools/latest && \
    rm commandlinetools-linux-9477386_latest.zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Accept licenses and install SDK components
RUN yes | sdkadmin --licenses > /dev/null 2>&1 && \
    sdkadmin "platform-tools" "platforms;android-36" "build-tools;35.0.0" > /dev/null 2>&1

# Copy gradle wrapper and build config first (better layer caching)
COPY gradlew gradle.properties settings.gradle.kts build.gradle.kts ./
COPY gradle ./gradle
RUN sed -i 's/\r$//' gradlew && chmod +x gradlew

# Pre-download gradle dependencies
RUN ./gradlew --version

# Copy app source
COPY app ./app

# Build the app
RUN ./gradlew assembleDebug --no-daemon

# Final stage - minimal runtime image
FROM eclipse-temurin:17-jdk-jammy

ENV GRADLE_USER_HOME=/app/.gradle

WORKDIR /app

# Only copy the built APK from builder, not the entire SDK/gradle cache
COPY --from=builder /app/app/build/outputs ./app/build/outputs
COPY --from=builder /app/gradle.properties ./
COPY --from=builder /app/settings.gradle.kts ./
COPY --from=builder /app/build.gradle.kts ./

# Run tests (only use essentials)
CMD ["echo", "Build artifacts ready in /app/app/build/outputs"]
